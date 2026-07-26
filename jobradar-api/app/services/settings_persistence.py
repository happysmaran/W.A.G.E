from __future__ import annotations

import json

from sqlmodel import Session

from app.models.db_models import SettingsDB

_CONFIG_KEY = "ollama_config"


def load_runtime_config(session: Session) -> dict | None:
    row = session.get(SettingsDB, _CONFIG_KEY)
    if not row:
        return None
    return json.loads(row.value)


def save_runtime_config(session: Session, config: dict) -> None:
    row = session.get(SettingsDB, _CONFIG_KEY)
    value = json.dumps(config)
    if row:
        row.value = value
    else:
        row = SettingsDB(key=_CONFIG_KEY, value=value)
    session.add(row)
    session.commit()
