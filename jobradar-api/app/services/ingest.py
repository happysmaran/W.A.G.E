from __future__ import annotations

from app.services.ollama_client import ollama_client
from app.services.parsing import clean_job_posting_text

INGEST_SYSTEM_PROMPT = """You clean up a raw copy-pasted job posting and extract structured fields.

People paste this straight from their browser, so it often contains noise mixed into the
actual posting: navigation menus, cookie banners, "Apply now" buttons repeated multiple
times, related-jobs sidebars, footer boilerplate, social share links.

Your job:
1. Extract the job title, exactly as stated.
2. Extract the hiring company name, exactly as stated. If genuinely not present anywhere
   in the text, return an empty string — do not guess.
3. Produce a cleaned version of the actual job description: responsibilities, requirements,
   qualifications, about-the-role/team content. Strip everything else (nav, footer, cookie
   notices, repeated CTAs, unrelated job listings). Do not summarize or paraphrase the
   substance — keep the real content close to verbatim, just with the noise removed.

Respond only with JSON: {"title": "string", "company": "string", "description": "string"}
"""


def _mock_ingest(raw_text: str) -> dict:
    # Deterministic mock: assume the text is already reasonably clean (as it
    # is in tests/dev fixtures) and pass it through, leaving title/company
    # blank so the caller's explicit hints (if any) are what's used.
    return {"title": "", "company": "", "description": clean_job_posting_text(raw_text)}


async def parse_pasted_job(raw_text: str, title_hint: str = "", company_hint: str = "") -> dict:
    """
    Takes whatever someone pasted in — often messy, copied straight from a
    browser tab — and returns a clean {title, company, description}.

    Explicit hints always win over what the model extracts: if the person
    typed a title/company in the form, that's authoritative and the model's
    extraction is only used to fill in whatever they left blank.
    """
    pre_cleaned = clean_job_posting_text(raw_text)

    # Heuristic for Greenhouse / Ashby titles from job discovery
    # e.g., "Job Application for Software Engineer at Stripe"
    if not company_hint and title_hint and " at " in title_hint:
        parts = title_hint.rsplit(" at ", 1)
        company_hint = parts[-1].strip()
        if title_hint.startswith("Job Application for "):
            title_hint = parts[0].replace("Job Application for ", "").strip()

    hints = []
    if title_hint: hints.append(f"Title hint: {title_hint}")
    if company_hint: hints.append(f"Company hint: {company_hint}")
    
    user_prompt = f"Raw pasted posting:\n{pre_cleaned}"
    if hints:
        user_prompt = "\n".join(hints) + "\n\n" + user_prompt

    result = await ollama_client.chat_json(
        system=INGEST_SYSTEM_PROMPT,
        user=user_prompt,
        mock_response=_mock_ingest(pre_cleaned),
    )

    return {
        "title": title_hint.strip() or result.get("title", "").strip(),
        "company": company_hint.strip() or result.get("company", "").strip(),
        "description": result.get("description", "").strip() or pre_cleaned,
    }
