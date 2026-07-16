from __future__ import annotations

from sqlmodel import Session, select

from app.models.db_models import JobDB, PersonaDB, ResumeChunkDB

SEED_PERSONAS = [
    PersonaDB(
        id="fullstack",
        name="Full-stack dev profile",
        salary_floor=150,
        work_modes=["remote", "hybrid"],
        excluded_industries=["defense"],
    ),
    PersonaDB(
        id="eng-manager",
        name="Engineering manager profile",
        salary_floor=190,
        work_modes=["hybrid"],
        excluded_industries=[],
    ),
]

SEED_RESUME_CHUNKS = [
    ResumeChunkDB(persona_id="fullstack", section="skills", text="Python FastAPI Celery async task queues Postgres schema design"),
    ResumeChunkDB(persona_id="fullstack", section="experience", text="Built backend services for internal tools using Python"),
    ResumeChunkDB(persona_id="fullstack", section="projects", text="Terraform infrastructure as code CI/CD pipeline ownership AWS"),
    ResumeChunkDB(persona_id="eng-manager", section="skills", text="Engineering leadership team management React GraphQL"),
    ResumeChunkDB(persona_id="eng-manager", section="experience", text="Led a team of 6 engineers shipping a patient-facing portal"),
]

SEED_JOBS = [
    JobDB(
        id="job-1",
        title="Senior Backend Engineer",
        company="Northwind Data",
        source="greenhouse",
        source_label="Greenhouse",
        score=91,
        tag="High skill overlap",
        status="inbox",
        matches=[
            {"id": "m1", "label": "Python + FastAPI, 4yr production use"},
            {"id": "m2", "label": "Async task queues (Celery)"},
            {"id": "m3", "label": "Postgres schema design"},
        ],
        gaps=[{"id": "g1", "label": "Company lists Kubernetes as required, resume shows Docker only", "severity": "minor"}],
        bullet_before="Built backend services for internal tools using Python.",
        bullet_after=(
            "Designed and shipped FastAPI microservices handling 2M+ daily async jobs via "
            "Celery, cutting task latency 40%."
        ),
        outreach_draft=(
            "Hi Priya, I came across the Senior Backend Engineer opening at Northwind and your "
            "recent post about the async migration caught my eye. I've spent the last two years "
            "building similar FastAPI + Celery pipelines and would welcome the chance to talk "
            "about how that experience could help the team. Open to a quick chat this week?"
        ),
        job_description=(
            "We're looking for a Senior Backend Engineer with FastAPI and Celery experience. "
            "Kubernetes experience required. Postgres schema design a plus."
        ),
    ),
    JobDB(
        id="job-2",
        title="Platform Engineer",
        company="Fieldstone Robotics",
        source="company-site",
        source_label="Company site",
        score=78,
        tag="Missing 1 core tool",
        status="inbox",
        matches=[
            {"id": "m1", "label": "Infra-as-code with Terraform"},
            {"id": "m2", "label": "CI/CD pipeline ownership"},
        ],
        gaps=[{"id": "g1", "label": "Role wants Go experience, resume shows only Python and TypeScript", "severity": "blocker"}],
        bullet_before="Managed cloud infrastructure and deployments.",
        bullet_after=(
            "Owned Terraform-based infra for 30+ services across 3 AWS accounts, reducing "
            "deploy time from 25 to 6 minutes."
        ),
        outreach_draft=(
            "Hi Marcus, Fieldstone's platform team posting mentioned rebuilding your deploy "
            "pipeline around Terraform, which lines up closely with a project I led last year. "
            "I'd love to trade notes and hear more about the role if you have 15 minutes."
        ),
        job_description="Platform Engineer role requiring Go, Terraform, and CI/CD ownership.",
    ),
    JobDB(
        id="job-3",
        title="Staff Software Engineer",
        company="Alderbrook Health",
        source="lever",
        source_label="Lever",
        score=64,
        tag="Company tech matches portfolio",
        status="reviewing",
        matches=[
            {"id": "m1", "label": "React + GraphQL frontend stack"},
            {"id": "m2", "label": "HIPAA-adjacent data handling experience"},
        ],
        gaps=[
            {"id": "g1", "label": "Job description emphasizes 8+ years, resume shows 5", "severity": "minor"},
            {"id": "g2", "label": "No direct healthcare-domain experience listed", "severity": "blocker"},
        ],
        bullet_before="Worked on frontend features for a healthcare product.",
        bullet_after=(
            "Led GraphQL schema redesign for a patient-facing portal serving 40k monthly "
            "active users under strict data-handling constraints."
        ),
        outreach_draft=(
            "Hi Dana, I noticed Alderbrook is hiring a Staff Engineer for the patient portal "
            "rebuild. My last two roles were React and GraphQL-heavy with sensitive data "
            "handling, and I'd value 15 minutes to learn more about the team's roadmap."
        ),
        job_description="Staff Software Engineer, 8+ years required, React/GraphQL, healthcare domain.",
    ),
]


def seed_if_empty(session: Session) -> None:
    existing = session.exec(select(PersonaDB)).first()
    if existing:
        return
    for persona in SEED_PERSONAS:
        session.add(persona)
    for chunk in SEED_RESUME_CHUNKS:
        session.add(chunk)
    for job in SEED_JOBS:
        session.add(job)
    session.commit()
