from __future__ import annotations

from fastapi import APIRouter

from app.services.embedding_client import embedding_model_state

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.get("/status")
async def get_embedding_status():
    """Status of the bundled local embedding model (used for resume/job
    matching). Independent of Ollama mode — this runs in-process either way.
    First run downloads a small (~130MB) ONNX model; the frontend can poll
    this to show a one-time 'preparing matching model' indicator instead of
    the first resume upload just silently hanging.
    """
    return embedding_model_state.to_dict()
