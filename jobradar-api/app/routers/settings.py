from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.services.runtime_config import runtime_config
from app.services.settings_persistence import save_runtime_config, load_runtime_config

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/status/setup")
async def get_setup_status(session: Session = Depends(get_session)):
    """Checks if the user has completed the first-run wizard."""
    saved = load_runtime_config(session)
    needs_setup = saved is None
    has_key = bool(saved and saved.get("api_key"))
    return {"needs_setup": needs_setup, "has_api_key": has_key}


class SettingsUpdate(BaseModel):
    mode: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    num_ctx: int | None = None
    mock_llm: bool | None = None


@router.get("")
async def get_settings():
    return runtime_config.state.public_dict()


@router.put("")
async def update_settings(payload: SettingsUpdate, session: Session = Depends(get_session)):
    updated = runtime_config.update(**payload.model_dump(exclude_unset=True))
    save_runtime_config(session, updated.model_dump())
    return updated.public_dict()
