from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.logging_config import logger
from app.models.db_models import FeedItemDB, JobDB, JobFeedDB
from app.services.scraper import (
    fetch_ashby_postings,
    fetch_greenhouse_postings,
    fetch_lever_postings,
)

# Each fetcher returns list[{title, company, source, url, description}] from a
# public ATS board API — structured JSON, no HTML scraping, no ToS grey area.
SOURCE_FETCHERS = {
    "greenhouse": fetch_greenhouse_postings,
    "lever": fetch_lever_postings,
    "ashby": fetch_ashby_postings,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _matches_keywords(title: str, keywords: str) -> bool:
    terms = [t.strip().lower() for t in keywords.split(",") if t.strip()]
    if not terms:
        return True
    lowered = title.lower()
    return any(term in lowered for term in terms)


async def poll_feed(session: Session, feed: JobFeedDB) -> int:
    """Fetches a feed's current postings, stages any not seen before as
    FeedItemDB rows, and returns how many were new. Dedupes against both
    previously-staged items and already-imported jobs for the same persona."""
    fetcher = SOURCE_FETCHERS.get(feed.source)
    if fetcher is None:
        raise ValueError(f"Unknown feed source '{feed.source}'")

    postings = await fetcher(feed.identifier)

    known_urls = {
        row.url
        for row in session.exec(
            select(FeedItemDB).where(FeedItemDB.persona_id == feed.persona_id)
        ).all()
    }
    known_urls |= {
        row.source_url
        for row in session.exec(
            select(JobDB).where(JobDB.persona_id == feed.persona_id)
        ).all()
        if row.source_url
    }

    label = feed.label or f"{feed.source}:{feed.identifier}"
    new_count = 0
    for posting in postings:
        url = (posting.get("url") or "").strip()
        if not url or url in known_urls:
            continue
        if not _matches_keywords(posting.get("title", ""), feed.keywords):
            continue
        session.add(
            FeedItemDB(
                id=str(uuid.uuid4())[:8],
                feed_id=feed.id,
                persona_id=feed.persona_id,
                title=posting.get("title", "").strip() or "(untitled)",
                company=posting.get("company", "").strip() or feed.identifier,
                url=url,
                description=posting.get("description", ""),
                source_label=label,
                first_seen_at=_now(),
                status="new",
            )
        )
        known_urls.add(url)
        new_count += 1

    feed.last_polled_at = _now()
    feed.last_status = f"ok: {new_count} new"
    session.add(feed)
    session.commit()
    return new_count


class FeedPoller:
    """Background loop that walks every enabled feed on a fixed interval.
    Started fire-and-forget from main.py's lifespan, mirroring the embedding
    warm-up task. Each cycle opens its own DB session."""

    def __init__(self) -> None:
        self.running = False
        self.last_run_at: str | None = None
        self.last_error: str | None = None
        self._task: asyncio.Task | None = None

    async def poll_all(self) -> dict:
        """One pass over all enabled feeds. Per-feed errors are recorded on
        the feed row and logged, never raised — one bad slug shouldn't stop
        the rest."""
        self.last_run_at = _now()
        totals = {"feeds": 0, "new_items": 0, "errors": 0}
        with Session(engine) as session:
            feeds = session.exec(select(JobFeedDB).where(JobFeedDB.enabled == True)).all()  # noqa: E712
            for feed in feeds:
                totals["feeds"] += 1
                try:
                    new_count = await poll_feed(session, feed)
                    totals["new_items"] += new_count
                    if new_count:
                        logger.info("feed %s (%s): %d new posting(s)", feed.id, feed.label, new_count)
                except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring
                    totals["errors"] += 1
                    feed.last_polled_at = _now()
                    feed.last_status = f"error: {exc}"
                    session.add(feed)
                    session.commit()
                    logger.warning("feed %s (%s) poll failed: %s", feed.id, feed.label, exc)
        return totals

    async def _loop(self, interval_seconds: int) -> None:
        self.running = True
        logger.info("feed poller started — every %ds", interval_seconds)
        try:
            while True:
                try:
                    result = await self.poll_all()
                    self.last_error = None
                    logger.info(
                        "feed poll cycle: %d feed(s), %d new, %d error(s)",
                        result["feeds"],
                        result["new_items"],
                        result["errors"],
                    )
                except Exception as exc:  # noqa: BLE001
                    self.last_error = str(exc)
                    logger.exception("feed poll cycle crashed")
                await asyncio.sleep(interval_seconds)
        finally:
            self.running = False

    def start(self) -> None:
        if not settings.feed_poll_enabled:
            logger.info("feed poller disabled (WAGE_FEED_POLL_ENABLED=false)")
            return
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop(settings.feed_poll_interval_seconds))


feed_poller = FeedPoller()
