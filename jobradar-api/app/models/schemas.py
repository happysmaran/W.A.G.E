from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class WorkMode(str, Enum):
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"


class JobStatus(str, Enum):
    inbox = "inbox"
    reviewing = "reviewing"
    applied = "applied"
    archived = "archived"


class JobSource(str, Enum):
    pasted = "pasted"
    discovered = "discovered"


class GapSeverity(str, Enum):
    blocker = "blocker"
    minor = "minor"


class OllamaMode(str, Enum):
    local = "local"
    cloud = "cloud"


class Persona(BaseModel):
    id: str
    name: str
    salary_floor: int = Field(alias="salaryFloor")
    work_modes: list[WorkMode] = Field(alias="workModes")
    excluded_industries: list[str] = Field(alias="excludedIndustries", default_factory=list)

    model_config = {"populate_by_name": True}


class PersonaCreate(BaseModel):
    name: str
    resume_text: str
    salary_floor: int
    work_modes: list[WorkMode]
    excluded_industries: list[str] = []


class MatchItem(BaseModel):
    id: str
    label: str


class GapItem(BaseModel):
    id: str
    label: str
    severity: GapSeverity


class Job(BaseModel):
    id: str
    persona_id: str = Field(alias="personaId")
    title: str
    company: str
    source: JobSource
    source_label: str = Field(alias="sourceLabel")
    score: int
    tag: str
    status: JobStatus
    matches: list[MatchItem]
    gaps: list[GapItem]
    bullet_before: str = Field(alias="bulletBefore")
    bullet_after: str = Field(alias="bulletAfter")
    outreach_draft: str = Field(alias="outreachDraft")
    applied_at: str | None = Field(alias="appliedAt", default=None)

    model_config = {"populate_by_name": True}


class JobStatusUpdate(BaseModel):
    status: JobStatus


class OllamaStatus(BaseModel):
    mode: OllamaMode
    model: str
    connected: bool


class ScoreRequest(BaseModel):
    persona_id: str
    job_description: str
    job_title: str
    company: str


class JobCreate(BaseModel):
    persona_id: str
    job_description: str
    title: str = ""  # optional — extracted from the pasted text if left blank
    company: str = ""  # optional — extracted from the pasted text if left blank


class TailorRequest(BaseModel):
    persona_id: str
    job_id: str


class OutreachRequest(BaseModel):
    persona_id: str
    job_id: str
    contact_name: str | None = None
    channel: str = "email"  # "email" | "linkedin"


class DiscoverRequest(BaseModel):
    query: str
    max_results: int = 10


class DiscoverResult(BaseModel):
    title: str
    url: str
    snippet: str = ""


class DiscoverImportRequest(BaseModel):
    persona_id: str
    url: str
    title_hint: str = ""
    company_hint: str = ""
