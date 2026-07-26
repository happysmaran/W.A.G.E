from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.models.schemas import OllamaMode, OllamaStatus
from app.services.ollama_client import ollama_client
from app.services.runtime_config import MODE_PRESETS, runtime_config
from app.services.settings_persistence import save_runtime_config

router = APIRouter(prefix="/ollama", tags=["ollama"])


class OllamaModeUpdate(BaseModel):
    mode: OllamaMode


@router.get("/status", response_model=OllamaStatus)
async def get_status():
    connected = await ollama_client.health()
    return OllamaStatus(mode=runtime_config.state.mode, model=runtime_config.state.model, connected=connected)


@router.patch("/status", response_model=OllamaStatus)
async def switch_mode(update: OllamaModeUpdate, session: Session = Depends(get_session)):
    """Switches between local/cloud-free/cloud-pro presets. Takes effect immediately, no restart needed."""
    if update.mode.value not in MODE_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {update.mode}")

    state = runtime_config.set_mode(update.mode.value)
    save_runtime_config(session, state.model_dump())
    connected = await ollama_client.health()
    return OllamaStatus(mode=state.mode, model=state.model, connected=connected)
