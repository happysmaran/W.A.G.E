from __future__ import annotations

from pydantic import BaseModel

from app.config import settings

MODE_PRESETS = {
    "local": {"base_url": "http://localhost:11434", "model": "llama3.1:8b"},
    "cloud-free": {"base_url": "https://ollama.com", "model": "llama3.1:8b-cloud"},
    "cloud-pro": {"base_url": "https://ollama.com", "model": "gpt-oss:120b-cloud"},
}


class RuntimeConfig(BaseModel):
    mode: str = "local"
    base_url: str = MODE_PRESETS["local"]["base_url"]
    api_key: str | None = None
    model: str = MODE_PRESETS["local"]["model"]
    embedding_model: str = "nomic-embed-text"
    num_ctx: int = 2048
    mock_llm: bool = True

    def public_dict(self) -> dict:
        """Same shape, with the API key masked for anything sent to a client."""
        data = self.model_dump()
        if data.get("api_key"):
            data["api_key"] = "•" * 8
        return data


class RuntimeConfigStore:
    """
    Single source of truth for every runtime-adjustable Ollama setting
    (connection, model choice, context size, mock mode). Seeded from
    environment defaults at startup, then mutable via the /settings API and
    persisted to the DB so changes survive a restart.
    """

    def __init__(self) -> None:
        initial_mode = "local" if "localhost" in settings.ollama_base_url else "cloud-pro"
        self.state = RuntimeConfig(
            mode=initial_mode,
            base_url=settings.ollama_base_url,
            api_key=settings.ollama_api_key,
            model=settings.ollama_model,
            embedding_model=settings.ollama_embedding_model,
            num_ctx=settings.ollama_num_ctx,
            mock_llm=settings.mock_llm,
        )

    def load(self, saved: dict) -> None:
        self.state = RuntimeConfig(**{**self.state.model_dump(), **saved})

    def set_mode(self, mode: str) -> RuntimeConfig:
        if mode not in MODE_PRESETS:
            raise ValueError(f"Unknown mode: {mode}")
        preset = MODE_PRESETS[mode]
        self.state = self.state.model_copy(update={"mode": mode, **preset})
        return self.state

    def update(self, **fields) -> RuntimeConfig:
        self.state = self.state.model_copy(update=fields)
        return self.state


runtime_config = RuntimeConfigStore()
