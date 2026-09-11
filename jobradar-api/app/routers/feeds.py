from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.models.db_models import FeedItemDB, JobDB, JobFeedDB, PersonaDB
from app.models.schemas import (
    FeedItem,
    FeedItemImportRequest,
    FeedPollStatus,
    Job,
    JobFeed,
    JobFeedCreate,
    JobFeedUpdate,
)
from app.services.ingest import parse_pasted_job
from app.services.job_feed import SOURCE_FETCHERS, feed_poller, poll_feed
from app.services.job_pipeline import job_to_schema, score_and_persist_job

router = APIRouter(prefix="/feeds", tags=["feeds"])


def _feed_to_schema(row: JobFeedDB) -> JobFeed:
    return JobFeed(
        id=row.id,
        personaId=row.persona_id,
        source=row.source,
        identifier=row.identifier,
        label=row.label or f"{row.source}:{row.identifier}",
        keywords=row.keywords,
        enabled=row.enabled,
        createdAt=row.created_at or None,
        lastPolledAt=row.last_polled_at,
        lastStatus=row.last_status,
    )


def _item_to_schema(row: FeedItemDB) -> FeedItem:
    return FeedItem(
        id=row.id,
        feedId=row.feed_id,
        personaId=row.persona_id,
        title=row.title,
        company=row.company,
        url=row.url,
        sourceLabel=row.source_label,
        firstSeenAt=row.first_seen_at or None,
        status=row.status,
    )


@router.get("", response_model=list[JobFeed])
def list_feeds(persona_id: str | None = None, session: Session = Depends(get_session)):
    query = select(JobFeedDB)
    if persona_id:
        query = query.where(JobFeedDB.persona_id == persona_id)
    return [_feed_to_schema(r) for r in session.exec(query).all()]


@router.post("", response_model=JobFeed)
def create_feed(payload: JobFeedCreate, session: Session = Depends(get_session)):
    if not session.get(PersonaDB, payload.persona_id):
        raise HTTPException(status_code=404, detail="Persona not found")
    if payload.source.value not in SOURCE_FETCHERS:
        raise HTTPException(status_code=400, detail=f"Unsupported feed source '{payload.source.value}'")

    identifier = payload.identifier.strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="A company slug or board URL is required.")

    existing = session.exec(
        select(JobFeedDB).where(
            JobFeedDB.persona_id == payload.persona_id,
            JobFeedDB.source == payload.source.value,
            JobFeedDB.identifier == identifier,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="That feed already exists for this persona.")

    row = JobFeedDB(
        id=str(uuid.uuid4())[:8],
        persona_id=payload.persona_id,
        source=payload.source.value,
        identifier=identifier,
        label=payload.label.strip(),
        keywords=payload.keywords.strip(),
        enabled=True,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _feed_to_schema(row)


@router.patch("/{feed_id}", response_model=JobFeed)
def update_feed(feed_id: str, payload: JobFeedUpdate, session: Session = Depends(get_session)):
    row = session.get(JobFeedDB, feed_id)
    if not row:
        raise HTTPException(status_code=404, detail="Feed not found")
    if payload.enabled is not None:
        row.enabled = payload.enabled
    if payload.keywords is not None:
        row.keywords = payload.keywords.strip()
    if payload.label is not None:
        row.label = payload.label.strip()
    session.add(row)
    session.commit()
    session.refresh(row)
    return _feed_to_schema(row)


@router.delete("/{feed_id}", status_code=204)
def delete_feed(feed_id: str, session: Session = Depends(get_session)):
    row = session.get(JobFeedDB, feed_id)
    if not row:
        raise HTTPException(status_code=404, detail="Feed not found")
    for item in session.exec(select(FeedItemDB).where(FeedItemDB.feed_id == feed_id)).all():
        session.delete(item)
    session.delete(row)
    session.commit()
    return None


@router.post("/{feed_id}/poll")
async def poll_feed_now(feed_id: str, session: Session = Depends(get_session)):
    """Run one poll of a single feed immediately, rather than waiting for the
    next background cycle."""
    row = session.get(JobFeedDB, feed_id)
    if not row:
        raise HTTPException(status_code=404, detail="Feed not found")
    try:
        new_count = await poll_feed(session, row)
    except ValueError as exc:
        row.last_status = f"error: {exc}"
        session.add(row)
        session.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        row.last_status = f"error: {exc}"
        session.add(row)
        session.commit()
        raise HTTPException(status_code=502, detail=f"Feed poll failed: {exc}") from exc
    return {"new_items": new_count}


@router.get("/items", response_model=list[FeedItem])
def list_feed_items(
    persona_id: str | None = None,
    status: str = "new",
    session: Session = Depends(get_session),
):
    query = select(FeedItemDB)
    if persona_id:
        query = query.where(FeedItemDB.persona_id == persona_id)
    if status:
        query = query.where(FeedItemDB.status == status)
    rows = session.exec(query).all()
    return [_item_to_schema(r) for r in sorted(rows, key=lambda r: r.first_seen_at, reverse=True)]


@router.post("/items/{item_id}/import", response_model=Job)
async def import_feed_item(
    item_id: str, payload: FeedItemImportRequest, session: Session = Depends(get_session)
):
    """Promote a staged posting into the scored jobs list — same parse+score
    pipeline as a manual paste or a one-off discovery import."""
    item = session.get(FeedItemDB, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Feed item not found")
    if not session.get(PersonaDB, payload.persona_id):
        raise HTTPException(status_code=404, detail="Persona not found")
    if item.status == "imported":
        raise HTTPException(status_code=409, detail="That posting was already imported.")

    cleaned = await parse_pasted_job(
        raw_text=item.description or item.title,
        title_hint=item.title,
        company_hint=item.company,
    )
    title = cleaned["title"] or item.title
    company = cleaned["company"] or item.company
    if not title or not company:
        raise HTTPException(
            status_code=422,
            detail="Couldn't determine a title and company for that posting.",
        )

    row = await score_and_persist_job(
        session,
        persona_id=payload.persona_id,
        title=title,
        company=company,
        description=cleaned["description"] or item.description,
        source="discovered",
        source_label=item.source_label or "Feed",
        source_url=item.url,
    )
    item.status = "imported"
    session.add(item)
    session.commit()
    return job_to_schema(row)


@router.post("/items/{item_id}/dismiss", status_code=204)
def dismiss_feed_item(item_id: str, session: Session = Depends(get_session)):
    item = session.get(FeedItemDB, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Feed item not found")
    item.status = "dismissed"
    session.add(item)
    session.commit()
    return None


@router.get("/status", response_model=FeedPollStatus)
def feed_status(session: Session = Depends(get_session)):
    feeds = session.exec(select(JobFeedDB)).all()
    items_new = len(session.exec(select(FeedItemDB).where(FeedItemDB.status == "new")).all())
    return FeedPollStatus(
        enabled=settings.feed_poll_enabled,
        intervalSeconds=settings.feed_poll_interval_seconds,
        running=feed_poller.running,
        lastRunAt=feed_poller.last_run_at,
        lastError=feed_poller.last_error,
        feedsTotal=len(feeds),
        feedsEnabled=len([f for f in feeds if f.enabled]),
        itemsNew=items_new,
    )
