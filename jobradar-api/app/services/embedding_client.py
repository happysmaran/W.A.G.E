from __future__ import annotations

import asyncio
import threading
from functools import lru_cache

# Small (~130MB), CPU-only, ONNX-based — no server, no GPU, no Ollama.
# Runs identically whether the user is in "local" or "cloud" chat mode:
# embeddings are no longer part of the local-vs-cloud decision at all.
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384


class _EmbeddingModelState:
    """Tracks first-run download/load progress so the frontend can show a
    status indicator instead of a resume upload just silently hanging while
    the ~130MB model is fetched.
    """

    def __init__(self) -> None:
        self.status: str = "not_started"  # not_started | loading | ready | error
        self.error: str | None = None
        self._lock = threading.Lock()

    def to_dict(self) -> dict:
        return {"status": self.status, "error": self.error}


embedding_model_state = _EmbeddingModelState()


@lru_cache(maxsize=1)
def _get_model():
    # Imported lazily so app startup doesn't pay the (one-time, ~130MB)
    # model-download/load cost unless embeddings are actually used, and so
    # environments without fastembed installed can still import this module.
    from fastembed import TextEmbedding

    with embedding_model_state._lock:
        embedding_model_state.status = "loading"
        embedding_model_state.error = None
    try:
        model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
    except Exception as exc:
        with embedding_model_state._lock:
            embedding_model_state.status = "error"
            embedding_model_state.error = str(exc)
        raise
    with embedding_model_state._lock:
        embedding_model_state.status = "ready"
    return model


class EmbeddingClient:
    """Local, in-process text embeddings — deliberately independent of the
    Ollama runtime_config (local/cloud). Ollama's cloud API has no embedding
    models (chat-only), so embeddings can't ride on the same local-vs-cloud
    switch as chat/scoring. Bundling a small ONNX model here removes Ollama
    as a dependency for this part of the pipeline entirely, in both modes.
    """

    async def embed(self, text: str) -> list[float]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._embed_sync, text)

    def _embed_sync(self, text: str) -> list[float]:
        model = _get_model()
        (vector,) = model.embed([text])
        return vector.tolist()

    async def warm_up(self) -> None:
        """Triggers the model download/load without embedding anything.
        Safe to call more than once — @lru_cache makes it a no-op after the
        first successful load. Call this at app startup so the download
        starts immediately rather than on the user's first resume upload.
        """
        if embedding_model_state.status in ("ready", "loading"):
            return
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, _get_model)
        except Exception:
            pass  # state already recorded; embed() will raise again for real callers


embedding_client = EmbeddingClient()

