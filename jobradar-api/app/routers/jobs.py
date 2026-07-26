from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models.db_models import JobDB, PersonaDB
from app.models.schemas import (
    Job,
    JobCreate,
    JobStatus,
    JobStatusUpdate,
    OutreachRequest,
    ScoreRequest,
    TailorRequest,
)
from app.services.ingest import parse_pasted_job
from app.services.scoring import score_job
from app.services.tailoring import generate_outreach_draft, generate_tailored_bullet
from app.services.vector_store import vector_index

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _to_schema(row: JobDB) -> Job:
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


@router.post("", response_model=Job)
async def create_job(payload: JobCreate, session: Session = Depends(get_session)):
    """Cleans a raw pasted job posting, scores it against the persona, and persists it."""
    persona = session.get(PersonaDB, payload.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    cleaned = await parse_pasted_job(
        raw_text=payload.job_description,
        title_hint=payload.title,
        company_hint=payload.company,
    )

    if not cleaned["title"] or not cleaned["company"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Couldn't find a job title and company in that text, and none were provided. "
                "Paste more of the posting (the header usually has both), or fill in the title "
                "and company fields directly."
            ),
        )

    result = await score_job(
        persona_id=payload.persona_id,
        job_title=cleaned["title"],
        company=cleaned["company"],
        job_description=cleaned["description"],
    )

    row = JobDB(
        id=str(uuid.uuid4())[:8],
        persona_id=payload.persona_id,
        title=cleaned["title"],
        company=cleaned["company"],
        source="pasted",
        source_label="Pasted",
        score=result["score"],
        tag=result["tag"],
        status="inbox",
        matches=result["matches"],
        gaps=result["gaps"],
        bullet_before="",
        bullet_after="",
        outreach_draft="",
        job_description=cleaned["description"],
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_schema(row)


@router.get("", response_model=list[Job])
async def list_jobs(
    persona_id: str | None = None, status: JobStatus | None = None, session: Session = Depends(get_session)
):
    query = select(JobDB)
    if persona_id:
        query = query.where(JobDB.persona_id == persona_id)
    if status:
        query = query.where(JobDB.status == status.value)
    rows = session.exec(query).all()
    return sorted([_to_schema(r) for r in rows], key=lambda j: j.score, reverse=True)


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str, session: Session = Depends(get_session)):
    row = session.get(JobDB, job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    session.delete(row)
    session.commit()
    return None


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: str, session: Session = Depends(get_session)):
    row = session.get(JobDB, job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_schema(row)


@router.patch("/{job_id}/status", response_model=Job)
async def update_job_status(job_id: str, update: JobStatusUpdate, session: Session = Depends(get_session)):
    row = session.get(JobDB, job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    row.status = update.status.value
    if update.status == JobStatus.applied:
        row.applied_at = datetime.now(timezone.utc).isoformat()
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_schema(row)


@router.post("/score")
async def score(request: ScoreRequest, session: Session = Depends(get_session)):
    """Baseline vector similarity plus LLM-generated match/gap breakdown for the explainability panel."""
    persona = session.get(PersonaDB, request.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    result = await score_job(
        persona_id=request.persona_id,
        job_title=request.job_title,
        company=request.company,
        job_description=request.job_description,
    )
    return result


@router.post("/tailor")
async def tailor(request: TailorRequest, session: Session = Depends(get_session)):
    row = session.get(JobDB, request.job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    # No bullet to tailor until we know which job — pull the closest
    # matching resume chunk on first request rather than at job creation.
    if not row.bullet_before:
        matches = await vector_index.best_matches(request.persona_id, row.job_description, top_k=1)
        if not matches:
            raise HTTPException(
                status_code=400,
                detail="No indexed resume content found for this persona — upload a resume first.",
            )
        row.bullet_before = matches[0][0]["text"]

    bullet_after = await generate_tailored_bullet(
        original_bullet=row.bullet_before,
        job_title=row.title,
        job_description=row.job_description,
    )
    row.bullet_after = bullet_after
    session.add(row)
    session.commit()
    return {"bullet_before": row.bullet_before, "bullet_after": bullet_after}


@router.post("/outreach")
async def outreach(request: OutreachRequest, session: Session = Depends(get_session)):
    row = session.get(JobDB, request.job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    matches = await vector_index.best_matches(request.persona_id, row.job_description, top_k=2)
    resume_summary = " ".join(chunk["text"] for chunk, _ in matches) if matches else ""

    message = await generate_outreach_draft(
        job_title=row.title,
        company=row.company,
        contact_name=request.contact_name,
        channel=request.channel,
        resume_summary=resume_summary,
    )
    row.outreach_draft = message
    session.add(row)
    session.commit()
    return {"message": message}
