# W.A.G.E API

FastAPI backend implementing the ingestion -> scoring -> tailoring -> outreach pipeline. Can be run standalone against mock data/LLM settings, so it can be smoke-tested with no Ollama instance available (this is for mainly debugging the UI - Ollama can be quite heavy sometimes).

## Setup

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive Swagger docs.

## Configuration

Two layers:

1. **Environment variables** (prefixed `WAGE_`, see `app/config.py` / `.env.example`) - seed the initial config on first run only.
2. **`GET`/`PUT /settings`** - the live, mutable config (Ollama URL, API key,
   models, context size, mock mode for testing). Changes apply immediately with no restart, and persist to the DB. This is what the frontend's settings panel talks to.

| Variable | Default | Purpose |
|---|---|---|
| `WAGE_OLLAMA_BASE_URL` | `http://localhost:11434` | `https://ollama.com` for Cloud |
| `WAGE_OLLAMA_API_KEY` | none | Required for Ollama Cloud |
| `WAGE_OLLAMA_MODEL` | `llama3.1:8b` | Chat/reasoning model |
| `WAGE_OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Must be embedding-capable — chat models can't produce embeddings |
| `WAGE_OLLAMA_NUM_CTX` | `4096` | Context window cap, keeps KV cache allocation predictable |
| `WAGE_MOCK_LLM` | `false` | Every LLM call returns deterministic canned data if set to `true` |

## Structure

- `app/services/ollama_client.py` — chat + embedding calls to Ollama. Reads connection details from `runtime_config` on every call, so settings changes apply live.
- `app/services/runtime_config.py` — the single mutable source of truth for Ollama connection/model/context settings, seeded from env vars and updatable via `/settings` or `/ollama/status` (mode presets).
- `app/services/settings_persistence.py` — loads/saves `runtime_config` to the DB so changes survive a restart.
- `app/services/parsing.py` — resume text extraction (pypdf) + semantic chunking, plus boilerplate stripping for pasted postings.
- `app/services/ingest.py` — cleans a raw pasted job posting and extracts title/company via LLM when not typed in.
- `app/services/vector_store.py` — in-memory embedding index with cosine similarity; stand-in for a real vector DB.
- `app/services/scoring.py` — fit score + explainable match/gap breakdown.
- `app/services/tailoring.py` — bullet rewriting and outreach draft generation.
- `app/db.py` / `app/models/db_models.py` — SQLite via SQLModel.
- `app/logging_config.py` — structured logging; a request-timing middleware in `main.py` logs method/path/status/duration for every request.
- `app/routers/` — HTTP layer. `POST /jobs` (paste-and-clean) is the only job-ingestion path — no automated scraping (tried, pulled — see below).

tldr; Create a persona (and upload a resume) and add jobs through the UI or API as described in the READMES.

## Why no automated scraping???

The original plan was to have Greenhouse/Lever API scraping and company-site HTML/headless-browser scraping, which were both originally built but then removed: API results were inconsistent across boards, JS-rendered career pages needed a full headless browser for fairly fragile payoff, and scraping career pages sits in a legal grey area regardless of technical robustness. Paste-and-clean (`services/ingest.py`) doesn't care what shape the source page was in, since a human already found and copied the posting.

## Known gaps

- SQLite → needs Postgres for concurrent multi-user access
- In-memory embedding index → needs real Qdrant/ChromaDB at scale
- No auth/session layer — every request is unscoped to any user
- Settings are global process state, not per-user
- `SIMILARITY_FLOOR`/`SIMILARITY_CEILING` in `scoring.py` are a rough calibration against `nomic-embed-text`, not a measured one (so it's kinda bad)
- No migration system (no Alembic) - `main.py` has an ad-hoc `ALTER TABLE` guard for the one column added post-hoc so far. I'm not planning on adding more, but probably should.

## !!! Model quality affects scoring more than you'd expect !!!

Gap/blocker classification is a hard judgment call, and through testing I found out that small models (1-2B params) are noticeably less reliable at it. They tend to over-flag "blockers" where a larger model would correctly call something "minor," or even worse, do the other way around. If a job you know you're a good fit for scores lower than one you aren't (or vice versa), that's most likely model quality, not calibration. You can change this by using a larger chat model, though, hence support for Ollama's very generous cloud API.
