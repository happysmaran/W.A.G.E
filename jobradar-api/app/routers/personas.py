from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from app.db import get_session
from app.models.db_models import JobDB, PersonaDB, ResumeChunkDB
from app.models.schemas import Persona, WorkMode
from app.services.parsing import chunk_resume, extract_text
from app.services.vector_store import vector_index

router = APIRouter(prefix="/personas", tags=["personas"])


def _to_schema(row: PersonaDB) -> Persona:
    return Persona(
        id=row.id,
        name=row.name,
        salaryFloor=row.salary_floor,
        workModes=row.work_modes,
        excludedIndustries=row.excluded_industries,
    )


@router.get("", response_model=list[Persona])
async def list_personas(session: Session = Depends(get_session)):
    rows = session.exec(select(PersonaDB)).all()
    return [_to_schema(r) for r in rows]


@router.get("/{persona_id}", response_model=Persona)
async def get_persona(persona_id: str, session: Session = Depends(get_session)):
    row = session.get(PersonaDB, persona_id)
    if not row:
        raise HTTPException(status_code=404, detail="Persona not found")
    return _to_schema(row)


@router.delete("/{persona_id}", status_code=204)
async def delete_persona(persona_id: str, session: Session = Depends(get_session)):
    row = session.get(PersonaDB, persona_id)
    if not row:
        raise HTTPException(status_code=404, detail="Persona not found")

    chunks = session.exec(select(ResumeChunkDB).where(ResumeChunkDB.persona_id == persona_id)).all()
    for chunk in chunks:
        session.delete(chunk)

    jobs = session.exec(select(JobDB).where(JobDB.persona_id == persona_id)).all()
    for job in jobs:
        session.delete(job)

    session.delete(row)
    session.commit()

    vector_index.remove_persona(persona_id)
    return None


@router.post("", response_model=Persona)
async def create_persona(
    name: str = Form(...),
    salary_floor: int = Form(...),
    work_modes: list[WorkMode] = Form(...),
    resume: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """
    Ingestion endpoint: accepts a resume file plus guardrail settings, extracts
    text, splits it into semantic chunks, persists both the persona and its
    chunks, and indexes the chunks into the (in-process) vector store.
    """
    persona_id = str(uuid.uuid4())[:8]
    raw_bytes = await resume.read()
    raw_text = extract_text(raw_bytes, resume.filename or "")
    chunks = chunk_resume(raw_text)

    row = PersonaDB(
        id=persona_id,
        name=name,
        salary_floor=salary_floor,
        work_modes=[m.value for m in work_modes],
        excluded_industries=[],
    )
    session.add(row)
    for chunk in chunks:
        session.add(ResumeChunkDB(persona_id=persona_id, section=chunk["section"], text=chunk["text"]))
    session.commit()

    await vector_index.index_resume(persona_id, chunks)

    return _to_schema(row)
