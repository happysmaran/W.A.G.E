from __future__ import annotations

import uuid

from app.services.ollama_client import ollama_client
from app.services.vector_store import vector_index

SCORING_SYSTEM_PROMPT = """You are a precise job-fit analyst. Given a candidate's resume \
chunks and a job description, identify concrete matches and concrete gaps.

Rules:
- Every match and gap must reference something specific and checkable (a named \
tool, years of experience, a domain, a certification) — never vague statements \
like "seems like a good fit".
- Mark a gap as "blocker" ONLY if the job description explicitly uses hard-requirement \
language ("required", "must have", "X+ years required") AND the resume shows no \
reasonably related experience at all. Default to "minor" whenever there's ambiguity —
a candidate with adjacent or partial experience is a minor gap, not a blocker.
- Seniority/experience-level mismatches for internships or entry-level roles are \
almost always "minor", not "blocker" — junior roles exist specifically for people \
who don't yet have years of experience.
- Respond only with JSON matching this exact shape, nothing else:
{"matches": [{"label": "string"}], "gaps": [{"label": "string", "severity": "blocker|minor"}]}
"""

# Cosine similarity for related professional text typically sits in a
# narrow band (~0.4-0.6), not near 1.0 — these anchors stretch that range
# out to a 0-100 score that reads sensibly. Rough calibration, not measured.
SIMILARITY_FLOOR = 0.15
SIMILARITY_CEILING = 0.65

# Capped so a couple of misclassified blockers can't crater an otherwise
# strong match to near-zero.
BLOCKER_PENALTY = 10
MAX_BLOCKER_PENALTY = 25


def _rescale_similarity(raw: float) -> float:
    stretched = (raw - SIMILARITY_FLOOR) / (SIMILARITY_CEILING - SIMILARITY_FLOOR)
    return max(0.0, min(1.0, stretched))


def _mock_gap_analysis(job_description: str) -> dict:
    return {
        "matches": [
            {"label": "Resume shows direct experience with the core language/framework mentioned"},
            {"label": "Prior role scope matches the seniority level of this posting"},
        ],
        "gaps": [
            {"label": "Job description names a required tool not found in the resume", "severity": "blocker"},
        ],
    }


async def score_job(persona_id: str, job_title: str, company: str, job_description: str) -> dict:
    """Produces a 0-100 fit score plus an explainable match/gap breakdown.

    The score comes from resume/JD vector similarity (a triage signal, not
    gospel); the match/gap list comes from LLM reasoning over the same
    inputs. Gap classification quality depends heavily on the chat model —
    small models (1-2B params) tend to over-flag "blocker" where a larger
    model would correctly call something "minor".
    """
    raw_similarity = await vector_index.overall_similarity(persona_id, job_description)
    baseline_score = round(_rescale_similarity(raw_similarity) * 100)

    analysis = await ollama_client.chat_json(
        system=SCORING_SYSTEM_PROMPT,
        user=f"Job title: {job_title}\nCompany: {company}\nJob description:\n{job_description}",
        mock_response=_mock_gap_analysis(job_description),
    )

    blocker_count = sum(1 for g in analysis.get("gaps", []) if g.get("severity") == "blocker")
    penalty = min(blocker_count * BLOCKER_PENALTY, MAX_BLOCKER_PENALTY)
    adjusted_score = max(0, baseline_score - penalty)

    matches = [{"id": str(uuid.uuid4())[:8], "label": m["label"]} for m in analysis.get("matches", [])]
    gaps = [
        {"id": str(uuid.uuid4())[:8], "label": g["label"], "severity": g["severity"]}
        for g in analysis.get("gaps", [])
    ]

    if adjusted_score >= 80:
        tag = "High skill overlap"
    elif adjusted_score >= 65:
        tag = "Missing 1 core tool" if blocker_count else "Strong overlap, minor gaps"
    else:
        tag = "Significant gaps"

    return {
        "score": adjusted_score,
        "tag": tag,
        "matches": matches,
        "gaps": gaps,
    }
