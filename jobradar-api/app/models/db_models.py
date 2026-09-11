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
    # Origin URL for jobs pulled from a feed / discovery, used to dedupe
    # against re-ingesting the same posting. Empty for pasted jobs.
    source_url: str = Field(default="", index=True)


class SettingsDB(SQLModel, table=True):
    __tablename__ = "settings"

    key: str = Field(primary_key=True)
    value: str


class JobFeedDB(SQLModel, table=True):
    """A saved subscription to a company's ATS board. The background poller
    walks every enabled feed on a timer and stages new postings as FeedItemDB
    rows for the persona to review."""

    __tablename__ = "job_feeds"

    id: str = Field(primary_key=True)
    persona_id: str = Field(index=True)
    source: str  # "greenhouse" | "lever" | "ashby"
    identifier: str  # company slug or board URL the user pasted
    label: str = Field(default="")  # display name; defaults to source:identifier
    keywords: str = Field(default="")  # comma-separated; matched case-insensitively against title
    enabled: bool = Field(default=True)
    created_at: str = Field(default="")
    last_polled_at: str | None = Field(default=None)
    last_status: str = Field(default="")  # "ok: N new" | "error: ..."


class FeedItemDB(SQLModel, table=True):
    """A posting found by a feed poll, staged for review. Nothing here is
    scored or added to the jobs table until the user imports it."""

    __tablename__ = "feed_items"

    id: str = Field(primary_key=True)
    feed_id: str = Field(index=True)
    persona_id: str = Field(index=True)
    title: str
    company: str
    url: str = Field(index=True)
    description: str = Field(default="")
    source_label: str = Field(default="")
    first_seen_at: str = Field(default="")
    status: str = Field(default="new")  # "new" | "imported" | "dismissed"
