from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.config import settings
from app.db import create_db_and_tables, engine
from app.logging_config import logger, setup_logging
from app.models.db_models import ResumeChunkDB
from app.routers import jobs, ollama, personas
from app.services.vector_store import vector_index

setup_logging()


def _migrate_add_missing_columns() -> None:
    """
    SQLModel's create_all only creates missing tables, not missing columns on
    existing tables — so a schema change like adding JobDB.persona_id won't
    apply to a jobradar.db file created by an earlier version. This is a
    minimal ad-hoc patch, not a real migration system (no Alembic set up
    yet); it only handles the specific columns this app has added post-hoc.
    Safe to run every startup — checks before altering.
    """
    with engine.connect() as conn:
        existing_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(jobs)")}
        if existing_columns and "persona_id" not in existing_columns:
            conn.exec_driver_sql("ALTER TABLE jobs ADD COLUMN persona_id TEXT DEFAULT ''")
            conn.commit()
            logger.info("migrated: added jobs.persona_id column")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    _migrate_add_missing_columns()
    with Session(engine) as session:
        # Rebuild the in-process vector index from persisted resume chunks.
        # The vector store itself is in-memory (see services/vector_store.py),
        # so it needs re-seeding from the DB on every process restart. No
        # fixture data is seeded here — personas and jobs only exist once a
        # real resume is uploaded and a real job is added or discovered.
        chunks = session.exec(select(ResumeChunkDB)).all()
        by_persona: dict[str, list[dict]] = {}
        for chunk in chunks:
            by_persona.setdefault(chunk.persona_id, []).append({"section": chunk.section, "text": chunk.text})
        for persona_id, persona_chunks in by_persona.items():
            try:
                await vector_index.index_resume(persona_id, persona_chunks)
            except Exception as exc:
                # Don't let a missing/unreachable Ollama model take the whole
                # API down at startup. Log it and continue — /jobs/score for
                # this persona will fail with a clear error until the model
                # is pulled and reachable, but everything else keeps working.
                logger.warning(
                    "Failed to index resume for persona '%s': %s\n"
                    "  This usually means the configured Ollama model isn't pulled yet, "
                    "or Ollama isn't running/reachable at the configured base URL.\n"
                    "  Run `ollama pull <model>` and `ollama list` to check, or set "
                    "JOBRADAR_MOCK_LLM=true to run without a live Ollama instance.",
                    persona_id,
                    exc,
                )

    logger.info("startup complete — mock_llm=%s ollama_base_url=%s", settings.mock_llm, settings.ollama_base_url)
    yield
    logger.info("shutting down")


app = FastAPI(
    title="JobRadar API",
    description="Ingestion, scoring, tailoring, and outreach pipeline for job search strategy.",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s -> %d (%.0fms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


app.include_router(personas.router)
app.include_router(jobs.router)
app.include_router(ollama.router)


@app.exception_handler(RuntimeError)
async def ollama_runtime_error_handler(request: Request, exc: RuntimeError):
    # services/ollama_client.py raises plain RuntimeError (not an
    # HTTPException) for anything Ollama-related — connection refused, model
    # not pulled, request rejected with a 500 from Ollama itself, etc. Catch
    # it here once so every endpoint that eventually calls into Ollama gets a
    # clean, readable 502 with the actual diagnostic message instead of a
    # bare unhandled-exception 500.
    logger.error("Ollama error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/")
async def root():
    return {
        "service": "jobradar-api",
        "version": app.version,
        "mock_llm": settings.mock_llm,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
