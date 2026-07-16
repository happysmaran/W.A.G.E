from __future__ import annotations

from pydantic import BaseModel

from app.config import settings

# Presets for the three modes described in the architecture doc. Cloud modes
# share a base URL/auth scheme; only the model differs by tier.
MODE_PRESETS = {
    "local": {
        "base_url": "http://localhost:11434",
        "model": "llama3.1:8b",
        "embedding_model": "nomic-embed-text",
    },
    "cloud-free": {
        "base_url": "https://ollama.com",
        "model": "llama3.1:8b-cloud",
        "embedding_model": "nomic-embed-text",
    },
    "cloud-pro": {
        "base_url": "https://ollama.com",
        "model": "gpt-oss:120b-cloud",
        "embedding_model": "nomic-embed-text",
    },
}


class OllamaRuntimeState(BaseModel):
    mode: str = "local"
    base_url: str = MODE_PRESETS["local"]["base_url"]
    model: str = MODE_PRESETS["local"]["model"]
    embedding_model: str = MODE_PRESETS["local"]["embedding_model"]


class OllamaRuntime:
    """
    Holds the currently active Ollama connection settings in memory, mutable
    via the /ollama/status PATCH endpoint. This lets the frontend's controller
    widget actually switch between local/cloud-free/cloud-pro at runtime
    instead of only reflecting a value baked in at process start.

    Not persisted across restarts by design for now — a restart falls back
    to JOBRADAR_OLLAMA_BASE_URL / JOBRADAR_OLLAMA_MODEL from the environment.
    Worth moving into the DB alongside a user/session concept once this is
    multi-user rather than single-desk-instance.
    """

    def __init__(self) -> None:
        initial_mode = "local" if "localhost" in settings.ollama_base_url else "cloud-pro"
        self.state = OllamaRuntimeState(
            mode=initial_mode,
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            embedding_model=settings.ollama_embedding_model,
        )

    def set_mode(self, mode: str) -> OllamaRuntimeState:
        if mode not in MODE_PRESETS:
            raise ValueError(f"Unknown mode: {mode}")
        preset = MODE_PRESETS[mode]
        self.state = OllamaRuntimeState(
            mode=mode,
            base_url=preset["base_url"],
            model=preset["model"],
            embedding_model=preset["embedding_model"],
        )
        return self.state


ollama_runtime = OllamaRuntime()
