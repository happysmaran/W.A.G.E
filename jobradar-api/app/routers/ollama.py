from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.schemas import OllamaMode, OllamaStatus
from app.services.ollama_client import ollama_client
from app.services.ollama_runtime import MODE_PRESETS, ollama_runtime

router = APIRouter(prefix="/ollama", tags=["ollama"])


class OllamaModeUpdate(BaseModel):
    mode: OllamaMode


@router.get("/status", response_model=OllamaStatus)
async def get_status():
    connected = await ollama_client.health()
    return OllamaStatus(mode=ollama_runtime.state.mode, model=ollama_runtime.state.model, connected=connected)


@router.patch("/status", response_model=OllamaStatus)
async def switch_mode(update: OllamaModeUpdate):
    """
    Switches the active Ollama connection (local daemon vs. cloud free/pro
    tier) at runtime. Takes effect on the next chat/embeddings call — no
    process restart needed, since app.services.ollama_client reads connection
    details from ollama_runtime.state on every request rather than caching
    them at startup.
    """
    if update.mode.value not in MODE_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {update.mode}")

    ollama_runtime.set_mode(update.mode.value)
    connected = await ollama_client.health()
    return OllamaStatus(mode=ollama_runtime.state.mode, model=ollama_runtime.state.model, connected=connected)
