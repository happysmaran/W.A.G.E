from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.services.parsing import clean_job_posting_text
from app.services.renderer import render_page_html

# Tier 1: structured ATS APIs. No scraping fragility, no ToS risk.
GREENHOUSE_BOARD_API = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
LEVER_BOARD_API = "https://api.lever.co/v0/postings/{company}"

# LinkedIn/Indeed are deliberately excluded — aggressive anti-bot posture and
# ToS terms make scraping them a liability rather than a data source.


def extract_board_slug(identifier: str) -> str:
    """
    Accepts either a bare slug ("stripe") or a full URL people naturally
    paste from their browser (https://job-boards.greenhouse.io/stripe,
    boards.greenhouse.io/stripe, https://jobs.lever.co/netflix/abc123) and
    returns just the company slug. Greenhouse in particular has moved
    company boards across a few different public hostnames over time
    (boards.greenhouse.io, job-boards.greenhouse.io) — the slug is what the
    API actually keys on, not the hostname, so normalizing this way is more
    robust than requiring one exact URL shape.
    """
    identifier = identifier.strip()
    if "://" not in identifier and "/" not in identifier:
        return identifier  # already a bare slug
    normalized = identifier if "://" in identifier else f"https://{identifier}"
    path_parts = [p for p in urlparse(normalized).path.split("/") if p]
    return path_parts[0] if path_parts else identifier


async def fetch_greenhouse_postings(identifier: str) -> list[dict]:
    company_slug = extract_board_slug(identifier)
    if settings.mock_scraper:
        return _mock_postings(company_slug, "greenhouse")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # content=true is required to get the full job description back —
        # without it Greenhouse returns titles/URLs only, with an empty body.
        response = await client.get(
            GREENHOUSE_BOARD_API.format(company=company_slug), params={"content": "true"}
        )
        if response.status_code == 404:
            raise ValueError(
                f"No Greenhouse board found for '{company_slug}'. Some companies run their public "
                f"careers page on a custom domain while keeping a different (or no) slug on "
                f"boards-api.greenhouse.io — if the company's careers page isn't literally at "
                f"job-boards.greenhouse.io/{company_slug}, this API won't have it. Try 'Company site' "
                f"instead with the direct posting URL."
            )
        response.raise_for_status()
        data = response.json()
        jobs = data.get("jobs", [])
        return [
            {
                "title": job["title"],
                "company": company_slug,
                "source": "greenhouse",
                "url": job.get("absolute_url", ""),
                "description": clean_job_posting_text(job.get("content", "")),
            }
            for job in jobs
        ]


async def fetch_lever_postings(identifier: str) -> list[dict]:
    company_slug = extract_board_slug(identifier)
    if settings.mock_scraper:
        return _mock_postings(company_slug, "lever")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            LEVER_BOARD_API.format(company=company_slug), params={"mode": "json"}
        )
        if response.status_code == 404:
            raise ValueError(
                f"No Lever board found for '{company_slug}'. This means api.lever.co has no postings "
                f"endpoint for that slug — either the company doesn't use Lever, or their public slug "
                f"differs from what's in the URL. Try 'Company site' instead with a direct posting URL."
            )
        response.raise_for_status()
        try:
            postings = response.json()
        except ValueError:
            raise ValueError(
                f"Lever returned a non-JSON response for '{company_slug}', which usually means that "
                f"slug doesn't have an active board. Try 'Company site' instead with a direct posting URL."
            )
        return [
            {
                "title": job["text"],
                "company": company_slug,
                "source": "lever",
                "url": job.get("hostedUrl", ""),
                "description": clean_job_posting_text(job.get("descriptionPlain", "")),
            }
            for job in postings
        ]


def _extract_from_json_ld(soup: BeautifulSoup) -> dict | None:
    """
    Many ATS-hosted and company career pages embed a schema.org JobPosting
    as JSON-LD for SEO (Google for Jobs requires this). When present, it's
    far more reliable than guessing from visible text — it directly gives
    title, hiring org name, and full description.
    """
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("@type") == "JobPosting":
                org = candidate.get("hiringOrganization", {})
                company = org.get("name", "") if isinstance(org, dict) else ""
                description_html = candidate.get("description", "")
                description_text = BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)
                return {
                    "title": candidate.get("title", ""),
                    "company": company,
                    "description": description_text,
                }
    return None


def _extract_from_meta_and_headings(soup: BeautifulSoup) -> dict:
    """Fallback when there's no JobPosting JSON-LD: OpenGraph tags, then <h1>, then <title>."""
    og_title = soup.find("meta", property="og:title")
    og_site = soup.find("meta", property="og:site_name")
    h1 = soup.find("h1")
    title_tag = soup.find("title")

    title = (og_title.get("content") if og_title else "") or (h1.get_text(strip=True) if h1 else "")
    company = og_site.get("content") if og_site else ""

    if not title and title_tag:
        title = title_tag.get_text(strip=True)

    body_text = soup.get_text(" ", strip=True)
    return {"title": title or "", "company": company or "", "description": body_text}


async def fetch_company_site(url: str) -> dict:
    """
    Tier 2 fallback for companies without a Greenhouse/Lever/Ashby board.

    Two passes:
    1. Fast path — plain HTTP GET, then try schema.org JobPosting JSON-LD,
       then OpenGraph/heading tags. Works for server-rendered pages, costs
       one HTTP request, no browser overhead.
    2. Slow path — if pass 1 finds no usable title, the page is very likely
       a JS-rendered SPA (React/Vue/etc. career pages are common — Stripe's
       postings are exactly this). Falls back to actually rendering the page
       in headless Chromium via services/renderer.py and re-running the same
       extraction against the rendered HTML.

    A genuine listings/search page (not one specific posting) will still
    fail both passes, since there's no single JobPosting to find — that's
    expected, not a bug to work around.
    """
    if settings.mock_scraper:
        return {
            "title": "Platform Engineer",
            "company": "Fieldstone Robotics",
            "source": "company-site",
            "url": url,
            "description": "Mock company-site posting body would be extracted and cleaned here.",
        }

    static_html = await _fetch_static_html(url)
    soup = BeautifulSoup(static_html, "html.parser")
    extracted = _extract_from_json_ld(soup) or _extract_from_meta_and_headings(soup)

    if not extracted["title"] or not extracted["company"]:
        try:
            rendered_html = await render_page_html(url)
            rendered_soup = BeautifulSoup(rendered_html, "html.parser")
            rendered_extracted = _extract_from_json_ld(rendered_soup) or _extract_from_meta_and_headings(
                rendered_soup
            )
            # Prefer whichever pass actually found something; rendering wins
            # on ties since it saw strictly more of the page.
            if rendered_extracted["title"] or rendered_extracted["company"]:
                extracted = rendered_extracted
        except RuntimeError as exc:
            # Playwright/Chromium not installed, or rendering itself failed
            # (timeout, blocked, etc). Don't fail the whole request over
            # it — fall through with whatever the static pass found (likely
            # nothing), which surfaces as the existing "couldn't determine
            # title/company" 400 asking for fallback fields. Print so it's
            # visible in server logs why JS rendering didn't help here.
            print(f"[scraper] Rendering fallback unavailable for {url}: {exc}")

    return {
        "title": extracted["title"],
        "company": extracted["company"],
        "source": "company-site",
        "url": url,
        "description": clean_job_posting_text(extracted["description"]),
    }


async def _fetch_static_html(url: str) -> str:
    async with httpx.AsyncClient(
        timeout=15.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (compatible; WAGE/0.1)"}
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def _mock_postings(company_slug: str, source: str) -> list[dict]:
    return [
        {
            "title": "Senior Backend Engineer",
            "company": company_slug,
            "source": source,
            "url": f"https://{source}.example.com/{company_slug}/1",
            "description": (
                "We're looking for a Senior Backend Engineer with FastAPI and Celery "
                "experience. Kubernetes experience required. Postgres schema design a plus."
            ),
        }
    ]
