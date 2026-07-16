# JobRadar API

FastAPI backend implementing the ingestion → scoring → tailoring → outreach
pipeline. Runs standalone against mock data/LLM out of the box so it can be
smoke-tested with no Ollama instance available yet.

## Setup

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive Swagger docs.

## Configuration

All config is via environment variables, prefixed `JOBRADAR_`. See `app/config.py`.

| Variable | Default | Purpose |
|---|---|---|
| `JOBRADAR_OLLAMA_BASE_URL` | `http://localhost:11434` | Point at `https://ollama.com` for Cloud |
| `JOBRADAR_OLLAMA_API_KEY` | none | Required for Ollama Cloud |
| `JOBRADAR_OLLAMA_MODEL` | `llama3.1:8b` | Chat/reasoning model — swap to `gpt-oss:120b-cloud` etc. for cloud |
| `JOBRADAR_OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Must be an embedding-capable model — chat models (deepseek-r1, llama3.1) can't produce embeddings |
| `JOBRADAR_MOCK_LLM` | `true` | Set `false` once a real Ollama endpoint is reachable |
| `JOBRADAR_OLLAMA_NUM_CTX` | `2048` | Context window cap sent with every chat request — keeps Ollama's KV cache allocation small and predictable rather than trusting its own (sometimes oversized) VRAM-based default |

With `MOCK_LLM=true` (the default), every endpoint returns deterministic
canned data — useful for frontend development without any external dependency.

## Structure

- `app/services/ollama_client.py` — single client used for both local and
  cloud Ollama, since the API shape is identical; reads connection details
  from `ollama_runtime` on every call so mode switches apply without a restart.
  Also exposes `embed()` for real text embeddings via `/api/embed`.
- `app/services/ollama_runtime.py` — mutable in-memory state for the active
  Ollama mode (local / cloud-free / cloud-pro), switchable via
  `PATCH /ollama/status`. Not persisted across restarts by design; falls back
  to `JOBRADAR_OLLAMA_BASE_URL`/`JOBRADAR_OLLAMA_MODEL` on process start.
- `app/services/parsing.py` — resume text extraction (pypdf) + semantic
  chunking, plus `clean_job_posting_text()` for stripping common boilerplate
  (equal-opportunity statements, copyright footers) from pasted postings.
- `app/services/ingest.py` — the job-adding pipeline: takes a raw pasted
  posting (often messy — nav menus, cookie banners, repeated "Apply now"
  buttons mixed in from a browser copy-paste), regex-strips obvious
  boilerplate, then uses the LLM to extract title/company (if not typed in)
  and produce a cleaned description body with the rest of the noise removed.
- `app/services/vector_store.py` — in-memory embedding index using real
  vectors from `ollama_client.embed()` (or a deterministic mock embedding in
  `MOCK_LLM` mode) with cosine similarity. Stand-in for a real
  Qdrant/ChromaDB deployment; swap the storage/search internals here and
  nothing in `scoring.py` needs to change.
- `app/services/scoring.py` — the explainability core: baseline similarity +
  LLM-generated match/gap breakdown, blockers penalized explicitly.
- `app/services/tailoring.py` — bullet rewriting and outreach draft generation.
- `app/db.py` / `app/models/db_models.py` — SQLite persistence via SQLModel.
  Auto-creates `jobradar.db` on first run; survives restarts.
- `app/routers/` — HTTP layer, one router per resource. `POST /jobs` is the
  only job-ingestion path — see "No automated scraping" below.

No fixture/dummy data is seeded — the app starts genuinely empty. Create a
persona (upload a resume) and add jobs through the UI or API before there's
anything to see.

## No automated scraping

An earlier version of this backend fetched postings automatically from
Greenhouse/Lever APIs and scraped company career pages (including a headless
Chromium fallback for JS-rendered SPAs). It was pulled:

- Greenhouse/Lever API results were inconsistent in practice — empty results
  for boards that clearly existed, unclear whether that meant "wrong slug"
  or "company restricts API access" or something else entirely
- Company-site scraping needed a full headless browser for most real career
  pages (React/Vue SPAs), which is heavy infrastructure for something this
  fragile, and ran into environment-specific issues (a Windows/uvicorn/
  Playwright event-loop conflict, for one)
- Scraping companies' career pages sits in a legal grey area ToS-wise,
  regardless of technical robustness

`POST /jobs` (paste-and-clean, via `services/ingest.py`) is the one ingestion
path now, and gets the investment instead: it doesn't care what shape the
source page was in, since a human already did the hard part of finding and
copying the posting.

## Known gaps before this is production-ready

- SQLite → fine for local dev, but needs Postgres for concurrent multi-user access
- In-memory embedding index → needs real Qdrant/ChromaDB once resume/job
  volume outgrows a single process's memory
- No auth/session layer — every request is currently unscoped to any user
- Ollama mode is global process state, not per-user — fine for a single-desk
  app, not for multi-tenant use
- The ingest LLM extraction (`services/ingest.py`) hasn't been tuned against
  a wide variety of real pasted postings yet
- The similarity rescaling constants in `services/scoring.py`
  (`SIMILARITY_FLOOR`/`SIMILARITY_CEILING`) are a rough calibration, not a
  measured one — worth re-tuning once you've scored a batch of real postings
  against a real embedding model and can see where genuinely strong/weak
  matches land
- No proper schema migration system (no Alembic) — `app/main.py` has a small
  ad-hoc `ALTER TABLE` guard for the one column added post-hoc so far
  (`jobs.persona_id`); further schema changes will need the same treatment
  or a real migration tool

## Model quality matters more than you'd expect

Gap/blocker classification (`services/scoring.py`) is a genuinely hard
judgment call, and small edge models (1-2B parameters) are noticeably less
reliable at it than larger ones — they tend to over-flag things as "blocker"
that a stronger model would correctly call "minor" or not mention at all.
The scoring prompt pushes toward conservative classification and the
blocker penalty is now capped rather than able to crater a score entirely,
but if scores still feel too harsh or a job you know you're a good fit for
scores lower than one you aren't, that's most likely model quality, not
just calibration — worth comparing behavior against a larger model
(`llama3.1:8b` or bigger) if `JOBRADAR_OLLAMA_MODEL` is currently pointed at
something small.
