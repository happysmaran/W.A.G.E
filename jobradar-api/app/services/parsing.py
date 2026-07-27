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
    "activities",
    "extracurriculars",
    "awards",
    "publications",
    "volunteering",
]

_BULLET_CHARS = ("–", "-", "•", "*")

# Matches a "Month YYYY" date (e.g. "Sep. 2025", "Apr 2024") or a bare
# "YYYY – YYYY"/"YYYY – Present" range. Entry title lines in the
# Experience/Projects sections of most resumes contain one of these; wrapped
# bullet-continuation lines almost never do, which is what lets us tell them
# apart without any layout/positional info (plain-text PDF extraction loses
# all of that).
_DATE_PATTERN = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s*\d{4}"
    r"|\b(19|20)\d{2}\s*[–-]\s*(Present|\d{4})",
    re.IGNORECASE,
)


def extract_text(file_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    # .txt / .md fallback
    return file_bytes.decode("utf-8", errors="ignore")


def _is_bullet_line(line: str) -> bool:
    return line.strip().startswith(_BULLET_CHARS)


def _is_date_line(line: str) -> bool:
    return bool(_DATE_PATTERN.search(line))


def chunk_resume(raw_text: str) -> list[dict]:
    """
    Splits resume text into semantic chunks keyed by detected section AND
    by individual entry within a section (each job, each project) — not
    just by section header.

    Plain-text PDF extraction gives us one line per visual line with no
    reliable signal for "this is a new entry" beyond the text itself, so
    entry boundaries are inferred heuristically:
      - a line starting with a bullet character is part of the current
        entry's bullet list
      - once bullets have started, a line containing a date (or whose very
        next line contains a date) signals the start of a new entry, e.g.
        a company/project name line immediately followed by a
        "Title — Date range" line
      - anything else is treated as a continuation of the current entry
        (either its header lines before any bullets, or a wrapped bullet
        that spilled onto a second physical line)

    This is a heuristic, not a full resume parser — it's tuned to the
    common "Company / Role — Date" and "Project Name | Stack   Date"
    conventions, not guaranteed to be perfect on every resume layout.
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    chunks: list[dict] = []
    current_section = "summary"
    buffer: list[str] = []
    seen_bullet = False

    def flush():
        nonlocal buffer, seen_bullet
        if buffer:
            chunks.append({"section": current_section, "text": " ".join(buffer)})
        buffer = []
        seen_bullet = False

    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        lowered = line.lower().strip(":#* ")

        if lowered in SECTION_HEADERS:
            flush()
            current_section = lowered
            i += 1
            continue

        if _is_bullet_line(line):
            buffer.append(line)
            seen_bullet = True
        elif not seen_bullet:
            # Still accumulating this entry's header lines (company name,
            # title + date, etc.) — no bullets seen yet, so nothing to
            # split from.
            buffer.append(line)
        elif _is_date_line(line):
            # A dated title line showing up right after the previous
            # entry's bullets — e.g. Projects, where "Name | Stack  Date"
            # is a single line. Starts a new entry.
            flush()
            buffer.append(line)
        else:
            # Ambiguous: either a wrapped continuation of the previous
            # bullet, or a new entry's lead-in line (e.g. a company name
            # with the date on the *next* line, as in Experience). Peek
            # ahead: if the next line has a date and isn't itself a new
            # section header, this line starts a new entry.
            next_line = lines[i + 1] if i + 1 < n else None
            next_is_new_entry_header = (
                next_line is not None
                and _is_date_line(next_line)
                and next_line.lower().strip(":#* ") not in SECTION_HEADERS
            )
            if next_is_new_entry_header:
                flush()
                buffer.append(line)
            else:
                buffer.append(line)
        i += 1

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
