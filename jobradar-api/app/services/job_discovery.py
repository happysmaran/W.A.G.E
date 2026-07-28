from __future__ import annotations

import httpx

from app.services.runtime_config import runtime_config

# Ollama's web_search/web_fetch are hosted endpoints on ollama.com, always
# called there regardless of whether chat is running in "local" or "cloud"
# mode — they need an Ollama account API key either way. This is
# deliberately independent of runtime_config.state.mode; it only cares
# whether an api_key is present.
DISCOVERY_BASE_URL = "https://ollama.com"

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

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        if runtime_config.state.mock_llm:
            return _MOCK_RESULTS[:max_results]
        self._require_key()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
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
            raise RuntimeError(f"Ollama web fetch returned {exc.response.status_code} for {url}.") from exc
        except httpx.ConnectError as exc:
            raise RuntimeError("Couldn't reach ollama.com for web fetch — check your internet connection.") from exc

        return data.get("content", "")


job_discovery_client = JobDiscoveryClient()
