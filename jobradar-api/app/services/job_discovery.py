from __future__ import annotations

import asyncio

import httpx
import trafilatura

from app.services.runtime_config import runtime_config
from app.services.renderer import render_page_html

# Ollama's web_search/web_fetch are hosted endpoints on ollama.com, always
# called there regardless of whether chat is running in "local" or "cloud"
# mode — they need an Ollama account API key either way. This is
# deliberately independent of runtime_config.state.mode; it only cares
# whether an api_key is present.
DISCOVERY_BASE_URL = "https://ollama.com"

# A bare query like "quant software developer" reads to a general web search
# as "pages about this profession/interest" — LinkedIn profiles, personal
# portfolio sites, "About me" pages — not "job postings for this role".
# Fanning the same query out across a handful of ATS platforms that only
# host actual postings (plus one job-board-biased generic query) fixes this
# without needing the user to phrase things any particular way.
JOB_BOARD_SITE_FILTERS = [
    "site:boards.greenhouse.io",
    "site:jobs.lever.co",
    "site:jobs.ashbyhq.com",
    "site:myworkdayjobs.com",
    "site:linkedin.com/jobs",
]

# URL substrings that are essentially never a job posting even when they
# show up in job-board-biased results (personal profiles, social feeds,
# portfolio homepages). Filtered out post-search rather than relied upon
# to not be returned in the first place.
_NON_POSTING_URL_MARKERS = (
    "linkedin.com/in/",
    "linkedin.com/pub/",
    "twitter.com/",
    "x.com/",
    "instagram.com/",
    "facebook.com/",
    "github.com/",  # profile/repo pages, not postings
)

_MOCK_RESULTS = [
    {
        "title": "Software Engineering Intern — Acme Robotics",
        "url": "https://example.com/jobs/acme-swe-intern",
        "snippet": "Acme Robotics is hiring a software engineering intern to work on flight "
        "control software and ground station tooling.",
    },
    {
        "title": "Backend Engineer, New Grad — Northwind Systems",
        "url": "https://example.com/jobs/northwind-backend",
        "snippet": "Northwind Systems seeks a new-grad backend engineer with Python and "
        "distributed systems experience.",
    },
]

_MOCK_PAGE_CONTENT = (
    "Software Engineering Intern — Acme Robotics\n\n"
    "Acme Robotics is looking for a Software Engineering Intern to join our ground "
    "station team. You'll work on telemetry pipelines, ArduPilot integration, and "
    "real-time sensor monitoring for autonomous aircraft.\n\n"
    "Requirements: Python, familiarity with robotics or embedded systems, currently "
    "pursuing a CS/EE degree. This is a mock result shown because job discovery is "
    "running in mock mode (no Ollama API key configured, or mock mode is on)."
)


class DiscoveryUnavailableError(RuntimeError):
    """Raised when discovery is used without an Ollama API key configured."""


# Used only for the fallback direct fetch below, when Ollama's hosted
# web_fetch fails. A real browser User-Agent (plus the headers that
# typically accompany it) gets past sites that block on a missing/bot-like
# UA — a fairly common reason a fetch 404s or 403s. It does NOT help with
# pages that are genuinely client-rendered (React/Vue SPA shells with no
# content in the initial HTML) — no UA spoofing substitutes for actually
# executing JavaScript; that would require a headless browser, which is the
# Playwright approach this project deliberately moved away from.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _is_likely_posting_url(url: str) -> bool:
    lowered = url.lower()
    return not any(marker in lowered for marker in _NON_POSTING_URL_MARKERS)


def _build_queries(query: str) -> list[str]:
    generic = f'{query} job posting "apply"'
    site_biased = [f"{filt} {query}" for filt in JOB_BOARD_SITE_FILTERS]
    return [generic, *site_biased]


class JobDiscoveryClient:
    def _headers(self) -> dict:
        api_key = runtime_config.state.api_key
        return {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def _require_key(self) -> None:
        if not runtime_config.state.mock_llm and not runtime_config.state.api_key:
            raise DiscoveryUnavailableError(
                "Job discovery needs an Ollama API key (Settings → Ollama). It's a hosted "
                "search/fetch call, so this is required even in local chat mode."
            )

    async def _raw_search(self, client: httpx.AsyncClient, query: str, max_results: int) -> list[dict]:
        try:
            response = await client.post(
                f"{DISCOVERY_BASE_URL}/api/web_search",
                headers=self._headers(),
                json={"query": query, "max_results": max_results},
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama web search returned {exc.response.status_code}. Check that your "
                f"API key is valid and has search access."
            ) from exc
        except httpx.ConnectError as exc:
            raise RuntimeError("Couldn't reach ollama.com for web search — check your internet connection.") from exc

        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")[:300],
            }
            for item in data.get("results", [])
        ]

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        """Searches for actual job postings, not pages about the role/field
        in general. Fans the query out across several ATS platforms
        (Greenhouse, Lever, Ashby, Workday, LinkedIn's own /jobs path) plus
        one job-posting-biased generic query, merges and dedupes by URL,
        and drops anything that's clearly a personal profile rather than a
        posting (linkedin.com/in/, github.com profile pages, social media).
        """
        if runtime_config.state.mock_llm:
            return _MOCK_RESULTS[:max_results]
        self._require_key()

        per_query_cap = max(3, max_results // 2)
        queries = _build_queries(query)

        async with httpx.AsyncClient(timeout=30.0) as client:
            batches = await asyncio.gather(
                *(self._raw_search(client, q, per_query_cap) for q in queries),
                return_exceptions=True,
            )

        seen_urls: set[str] = set()
        merged: list[dict] = []
        last_error: Exception | None = None
        for batch in batches:
            if isinstance(batch, Exception):
                last_error = batch
                continue
            for result in batch:
                url = result.get("url")
                if not url:
                    continue

                if "boards.greenhouse.io/embed/job_app" in url:
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(url)
                    params = parse_qs(parsed.query)
                    company = params.get("for", [""])[0]
                    token = params.get("token", [""])[0]
                    if company and token:
                        url = f"https://boards.greenhouse.io/{company}/jobs/{token}"
                        result["url"] = url

                if url in seen_urls or not _is_likely_posting_url(url):
                    continue
                seen_urls.add(url)
                merged.append(result)

        if not merged and last_error is not None:
            # Every single query failed (e.g. bad API key) — surface that
            # instead of silently returning an empty list.
            raise last_error

        return merged[:max_results]

    async def _ollama_fetch(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{DISCOVERY_BASE_URL}/api/web_fetch",
                headers=self._headers(),
                json={"url": url},
            )
            response.raise_for_status()
            return response.json().get("content", "")

    async def _direct_fetch(self, url: str) -> str:
        """Fallback for when Ollama's hosted fetch fails: a plain HTTP GET
        with a real browser User-Agent, then trafilatura strips it down to
        the main readable content the same way Ollama's fetch would have.
        Only helps when the original failure was bot-blocking, not when the
        page is a genuine client-rendered SPA shell (see module docstring
        on _BROWSER_HEADERS).
        """
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=_BROWSER_HEADERS) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
        return extracted or ""

    async def _render_fetch(self, url: str) -> str:
        """Final fallback for JS-rendered SPA career pages. Spins up a headless Chromium
        browser to render the page fully before extracting text.
        """
        html = await render_page_html(url)
        extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
        return extracted or ""

    async def fetch(self, url: str) -> str:
        """Returns cleaned, readable page content. Tries Ollama's hosted
        web_fetch first (it does readability extraction server-side); if
        that fails, falls back to a direct fetch with a browser User-Agent
        plus local extraction via trafilatura. The fallback rescues cases
        where a site specifically blocks Ollama's fetcher (bot detection on
        UA/headers) but not a real browser; it can't rescue pages that are
        genuinely empty without JavaScript execution.
        """
        if runtime_config.state.mock_llm:
            return _MOCK_PAGE_CONTENT
        self._require_key()

        ollama_error: Exception | None = None
        try:
            content = await self._ollama_fetch(url)
            if content.strip():
                return content
        except httpx.HTTPStatusError as exc:
            ollama_error = exc
        except httpx.ConnectError as exc:
            raise RuntimeError("Couldn't reach ollama.com for web fetch — check your internet connection.") from exc

        try:
            content = await self._direct_fetch(url)
            if content.strip():
                return content
        except Exception:
            pass  # fall through to the render fetch below

        try:
            content = await self._render_fetch(url)
            if content.strip():
                return content
        except Exception:
            pass  # fall through to the combined error below

        status_note = (
            f"HTTP {ollama_error.response.status_code} from Ollama's fetch"
            if isinstance(ollama_error, httpx.HTTPStatusError)
            else "no readable content"
        )
        raise RuntimeError(
            f"Couldn't fetch that page ({status_note}), and both a direct fetch and a headless "
            f"browser fallback failed to extract readable content. The page might be protected "
            f"against bots, or not contain text formatted like a job posting. Try a different "
            f"result, or open the link directly in a browser."
        )


job_discovery_client = JobDiscoveryClient()

