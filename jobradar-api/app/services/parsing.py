from __future__ import annotations

import io
import re

from pypdf import PdfReader

SECTION_HEADERS = [
    "experience",
    "work experience",
    "employment",
    "skills",
    "technical skills",
    "projects",
    "education",
    "summary",
    "leadership",
    "certifications",
]


def extract_text(file_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    # .txt / .md fallback
    return file_bytes.decode("utf-8", errors="ignore")


def chunk_resume(raw_text: str) -> list[dict]:
    """
    Splits resume text into semantic chunks keyed by detected section, so
    downstream scoring can weight "skills" matches differently from
    "project achievements" or generic prose.
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    chunks: list[dict] = []
    current_section = "summary"
    buffer: list[str] = []

    def flush():
        if buffer:
            chunks.append({"section": current_section, "text": " ".join(buffer)})
            buffer.clear()

    for line in lines:
        lowered = line.lower().strip(":#* ")
        if lowered in SECTION_HEADERS:
            flush()
            current_section = lowered
        else:
            buffer.append(line)
    flush()

    return chunks


def clean_job_posting_text(raw_text: str) -> str:
    """Strips common footer boilerplate from scraped job postings."""
    boilerplate_patterns = [
        r"equal opportunity employer.*",
        r"we are an equal opportunity.*",
        r"apply now.*",
        r"©\s?\d{4}.*",
    ]
    text = raw_text
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()
