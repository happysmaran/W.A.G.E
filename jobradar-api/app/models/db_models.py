from __future__ import annotations

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class PersonaDB(SQLModel, table=True):
    __tablename__ = "personas"

    id: str = Field(primary_key=True)
    name: str
    salary_floor: int
    work_modes: list[str] = Field(sa_column=Column(JSON), default_factory=list)
    excluded_industries: list[str] = Field(sa_column=Column(JSON), default_factory=list)


class ResumeChunkDB(SQLModel, table=True):
    __tablename__ = "resume_chunks"

    id: int | None = Field(default=None, primary_key=True)
    persona_id: str = Field(foreign_key="personas.id", index=True)
    section: str
    text: str


class JobDB(SQLModel, table=True):
    __tablename__ = "jobs"

    id: str = Field(primary_key=True)
    persona_id: str = Field(default="", index=True)
    title: str
    company: str
    source: str
    source_label: str
    score: int
    tag: str
    status: str
    matches: list[dict] = Field(sa_column=Column(JSON), default_factory=list)
    gaps: list[dict] = Field(sa_column=Column(JSON), default_factory=list)
    bullet_before: str
    bullet_after: str
    outreach_draft: str
    applied_at: str | None = Field(default=None)
    job_description: str = Field(default="")
