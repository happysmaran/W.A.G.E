from __future__ import annotations

from app.services.ollama_client import ollama_client

TAILOR_SYSTEM_PROMPT = """You rewrite a single resume bullet to better match a target job \
description, using only facts already present in the original bullet or resume context — \
never invent achievements, metrics, or tools the candidate didn't mention.
Respond only with JSON: {"bullet_after": "string"}
"""

OUTREACH_SYSTEM_PROMPT = """You draft a short, specific cold outreach message (email or \
LinkedIn note) from a job candidate to someone at a company they're applying to.

Rules:
- Reference something concrete and specific to the company or role, not generic flattery.
- Keep it short: under 500 characters for LinkedIn, under 120 words for email.
- End with a low-pressure, specific call to action (e.g. "open to a 15 minute chat").
- This is a DRAFT the candidate will personally review and edit before sending — write it
  as a strong starting point, not a finished, ready-to-blast message.
Respond only with JSON: {"message": "string"}
"""


async def generate_tailored_bullet(original_bullet: str, job_title: str, job_description: str) -> str:
    result = await ollama_client.chat_json(
        system=TAILOR_SYSTEM_PROMPT,
        user=(
            f"Original bullet: {original_bullet}\n"
            f"Target role: {job_title}\n"
            f"Job description: {job_description}"
        ),
        mock_response={
            "bullet_after": (
                "Designed and shipped FastAPI microservices handling 2M+ daily async jobs "
                "via Celery, cutting task latency 40%."
            )
        },
    )
    return result["bullet_after"]


async def generate_outreach_draft(
    job_title: str, company: str, contact_name: str | None, channel: str, resume_summary: str
) -> str:
    result = await ollama_client.chat_json(
        system=OUTREACH_SYSTEM_PROMPT,
        user=(
            f"Role: {job_title} at {company}\n"
            f"Contact: {contact_name or 'unknown, address generically'}\n"
            f"Channel: {channel}\n"
            f"Candidate background: {resume_summary}"
        ),
        mock_response={
            "message": (
                f"Hi{' ' + contact_name if contact_name else ''}, I came across the {job_title} "
                f"opening at {company} and wanted to reach out directly. My background lines up "
                "closely with what the role needs, and I'd welcome the chance to talk about how "
                "that experience could help the team. Open to a quick chat this week?"
            )
        },
    )
    return result["message"]
