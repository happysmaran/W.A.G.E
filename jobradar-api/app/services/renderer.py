from __future__ import annotations

import asyncio
import concurrent.futures
import sys


async def render_page_html(url: str, timeout_ms: int = 20000) -> str:
    """
    Renders a URL in a real (headless) browser and returns the resulting
    HTML — i.e. what you'd see in DevTools after JS has run, not just the
    server-sent skeleton a plain httpx GET returns.

    Needed for SPA career pages (Stripe's job postings are a React app that
    fetches content client-side; the raw HTML has none of it). Static
    BeautifulSoup parsing in scraper.py stays the fast/cheap first attempt —
    this is the fallback when that comes up empty.

    Requires the Playwright Python package AND its Chromium binary:
        pip install playwright
        playwright install chromium

    Runs in a dedicated background thread with its own event loop, rather
    than directly on whatever loop is already running. This sidesteps a
    Windows-specific conflict: Playwright launches its browser as a
    subprocess, which needs ProactorEventLoop, but uvicorn's default loop on
    Windows is SelectorEventLoop — which raises NotImplementedError the
    instant anything tries to spawn a subprocess on it. Since uvicorn creates
    its loop before this module is even imported, setting the event loop
    policy here wouldn't take effect in time; running in an isolated thread
    with its own explicitly-Proactor loop sidesteps the problem entirely
    rather than racing against uvicorn's startup order.
    """
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, _render_in_new_loop, url, timeout_ms)


def _render_in_new_loop(url: str, timeout_ms: int) -> str:
    """Runs on a worker thread: creates a fresh event loop (Proactor on Windows) and drives it."""
    if sys.platform == "win32":
        new_loop = asyncio.ProactorEventLoop()
    else:
        new_loop = asyncio.new_event_loop()

    try:
        asyncio.set_event_loop(new_loop)
        return new_loop.run_until_complete(_render_async(url, timeout_ms))
    finally:
        new_loop.close()


async def _render_async(url: str, timeout_ms: int) -> str:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright isn't installed. Run `pip install playwright` in the backend "
            "environment, then `playwright install chromium`, and retry."
        ) from exc

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page(
                    user_agent="Mozilla/5.0 (compatible; WAGE/0.1; +https://github.com)"
                )
                await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                return await page.content()
            finally:
                await browser.close()
    except Exception as exc:
        message = str(exc)
        if "Executable doesn't exist" in message or "playwright install" in message:
            raise RuntimeError(
                "Playwright's Chromium browser isn't installed. Run `playwright install "
                "chromium` in the backend environment (this downloads the actual browser "
                "binary — the pip package alone doesn't include it), then retry."
            ) from exc
        raise RuntimeError(f"Rendering {url} failed: {message}") from exc
