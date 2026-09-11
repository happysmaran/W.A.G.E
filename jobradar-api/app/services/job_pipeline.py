from __future__ import annotations

import uuid

from sqlmodel import Session

from app.models.db_models import JobDB
from app.models.schemas import Job
from app.services.scoring import score_job


def job_to_schema(row: JobDB) -> Job:
    return Job(
        id=row.id,
        personaId=row.persona_id,
        title=row.title,
        company=row.company,
        source=row.source,
        sourceLabel=row.source_label,
        score=row.score,
        tag=row.tag,
        status=row.status,
        matches=row.matches,
        gaps=row.gaps,
        bulletBefore=row.bullet_before,
        bulletAfter=row.bullet_after,
        outreachDraft=row.outreach_draft,
        appliedAt=row.applied_at,
    )


async def score_and_persist_job(
    session: Session,
    persona_id: str,
    title: str,
    company: str,
    description: str,
    source: str,
    source_label: str,
    source_url: str = "",
) -> JobDB:
    """Scores a posting against a persona and writes it to the jobs table.
    Shared by the paste path, one-off discovery, and feed imports."""
    result = await score_job(
        persona_id=persona_id,
        job_title=title,
        company=company,
        job_description=description,
    )
    row = JobDB(
        id=str(uuid.uuid4())[:8],
        persona_id=persona_id,
        title=title,
        company=company,
        source=source,
        source_label=source_label,
        score=result["score"],
        tag=result["tag"],
        status="inbox",
        matches=result["matches"],
        gaps=result["gaps"],
        bullet_before="",
        bullet_after="",
        outreach_draft="",
        job_description=description,
        source_url=source_url,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
