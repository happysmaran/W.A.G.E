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
from app.routers import jobs, ollama, personas, settings as settings_router
from app.services.runtime_config import runtime_config
from app.services.settings_persistence import load_runtime_config
from app.services.vector_store import vector_index

setup_logging()


def _migrate_add_missing_columns() -> None:
    """Ad-hoc column migration — SQLModel's create_all only creates missing tables, not columns."""
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
        saved_config = load_runtime_config(session)
        if saved_config:
            runtime_config.load(saved_config)

        # Vector index is in-memory, so rebuild it from persisted resume
        # chunks on every restart. Skips silently if Ollama isn't reachable
        # for a given persona - that persona's scoring will error clearly
        # later rather than blocking the whole app from starting.
        chunks = session.exec(select(ResumeChunkDB)).all()
        by_persona: dict[str, list[dict]] = {}
        for chunk in chunks:
            by_persona.setdefault(chunk.persona_id, []).append({"section": chunk.section, "text": chunk.text})
        for persona_id, persona_chunks in by_persona.items():
            try:
                await vector_index.index_resume(persona_id, persona_chunks)
            except Exception as exc:
                logger.warning("Failed to index resume for persona '%s': %s", persona_id, exc)

    logger.info("startup complete — mock_llm=%s base_url=%s", runtime_config.state.mock_llm, runtime_config.state.base_url)
    yield
    logger.info("shutting down")


app = FastAPI(
    title="JobRadar API",
    description="Ingestion, scoring, tailoring, and outreach pipeline for job search strategy.",
    version="0.4.0",
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
app.include_router(settings_router.router)


@app.exception_handler(RuntimeError)
async def ollama_runtime_error_handler(request: Request, exc: RuntimeError):
    """Ollama-related failures raise plain RuntimeError; surface as a clean 502 instead of an unhandled 500."""
    logger.error("Ollama error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/")
async def root():
    return {"service": "jobradar-api", "version": app.version, "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}
