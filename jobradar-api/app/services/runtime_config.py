from __future__ import annotations

from pydantic import BaseModel

from app.config import settings

# Ollama's cloud API has no product-tier gating on the client side — it's
# just "have an API key, pick any model." There used to be a fake
# cloud-free/cloud-pro split here standing in for "small model" vs "big
# model", which isn't a mode, it's a model choice. Collapsed to one `cloud`
# mode with a curated model list (see CLOUD_MODELS) instead.
MODE_PRESETS = {
    "local": {"base_url": "http://localhost:11434", "model": "llama3.1:8b"},
    "cloud": {"base_url": "https://ollama.com", "model": "gpt-oss:20b-cloud"},
}

# Curated list of Ollama cloud chat models, for a model picker in cloud mode.
# Not exhaustive — Ollama adds/retires cloud models over time; this is a
# reasonable default set as of mid-2026.
CLOUD_MODELS = [
    "gpt-oss:20b-cloud",
    "gpt-oss:120b-cloud",
    "qwen3-coder:480b-cloud",
    "glm-4.6:cloud",
    "deepseek-v3.1:671b-cloud",
    "kimi-k2:1t-cloud",
]


class RuntimeConfig(BaseModel):
    mode: str = "local"
    base_url: str = MODE_PRESETS["local"]["base_url"]
    api_key: str | None = None
    model: str = MODE_PRESETS["local"]["model"]
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
    Single source of truth for every runtime-adjustable Ollama chat setting
    (connection, model choice, context size, mock mode). Seeded from
    environment defaults at startup, then mutable via the /settings API and
    persisted to the DB so changes survive a restart.

    Note: this only governs chat/scoring. Embeddings are handled entirely
    separately by services/embedding_client.py, which runs in-process and
    doesn't care whether this store is set to local or cloud.
    """

    def __init__(self) -> None:
        initial_mode = "local" if "localhost" in settings.ollama_base_url else "cloud"
        self.state = RuntimeConfig(
            mode=initial_mode,
            base_url=settings.ollama_base_url,
            api_key=settings.ollama_api_key,
            model=settings.ollama_model,
            num_ctx=settings.ollama_num_ctx,
            mock_llm=settings.mock_llm,
        )

    def load(self, saved: dict) -> None:
        # Drop any stale embedding_model key from configs persisted before
        # this field was removed, so validation doesn't choke on it.
        saved = {k: v for k, v in saved.items() if k in RuntimeConfig.model_fields}
        self.state = RuntimeConfig(**{**self.state.model_dump(), **saved})

    def set_mode(self, mode: str) -> RuntimeConfig:
        if mode not in MODE_PRESETS:
            raise ValueError(f"Unknown mode: {mode}")
        preset = MODE_PRESETS[mode]
        self.state = self.state.model_copy(update={"mode": mode, **preset})
        return self.state

    def update(self, **fields) -> RuntimeConfig:
        fields.pop("embedding_model", None)  # stale field from old clients/persisted configs; ignore
        self.state = self.state.model_copy(update=fields)
        return self.state


runtime_config = RuntimeConfigStore()
