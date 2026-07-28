from __future__ import annotations

import asyncio

import httpx

from app.services.runtime_config import runtime_config

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
                url = result["url"]
                if not url or url in seen_urls or not _is_likely_posting_url(url):
                    continue
                seen_urls.add(url)
                merged.append(result)

        if not merged and last_error is not None:
            # Every single query failed (e.g. bad API key) — surface that
            # instead of silently returning an empty list.
            raise last_error

        return merged[:max_results]

    async def fetch(self, url: str) -> str:
        """Returns cleaned, readable page content (Ollama does the
        readability extraction server-side — this is what makes this a
        viable replacement for Playwright + manual HTML scraping)."""
        if runtime_config.state.mock_llm:
            return _MOCK_PAGE_CONTENT
        self._require_key()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{DISCOVERY_BASE_URL}/api/web_fetch",
                    headers=self._headers(),
                    json={"url": url},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Couldn't fetch that page (HTTP {exc.response.status_code}). Some job boards render "
                f"listings client-side via JavaScript, which a plain fetch can't execute — try a "
                f"different result, or open the link directly in a browser."
            ) from exc
        except httpx.ConnectError as exc:
            raise RuntimeError("Couldn't reach ollama.com for web fetch — check your internet connection.") from exc

        return data.get("content", "")


job_discovery_client = JobDiscoveryClient()

