from __future__ import annotations

import hashlib
import json
import struct

import httpx

from app.config import settings
from app.services.ollama_runtime import ollama_runtime

EMBEDDING_DIM = 256


class OllamaClient:
    """
    Thin wrapper around Ollama's /api/chat and /api/embeddings endpoints.

    Reads connection details from ollama_runtime rather than capturing them
    once at construction time, so switching modes via PATCH /ollama/status
    takes effect on the very next call with no restart needed.
    """

    def __init__(self) -> None:
        self.mock = settings.mock_llm

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if settings.ollama_api_key:
            headers["Authorization"] = f"Bearer {settings.ollama_api_key}"
        return headers

    async def chat_json(self, system: str, user: str, mock_response: dict) -> dict:
        """
        Sends a chat completion request constrained to JSON output.
        Falls back to a caller-supplied canned response when mock_llm is set,
        so routes remain testable without a live Ollama instance.
        """
        if self.mock:
            return mock_response

        state = ollama_runtime.state
        # Defensive cap: a long pasted job posting (plus system prompt) can
        # exceed a small model's context window. Ollama's behavior on
        # overflow varies by model/version — sometimes a clean truncation,
        # sometimes an internal 500 — so it's safer to truncate ourselves
        # than trust every model to handle it gracefully.
        MAX_USER_CHARS = 6000
        if len(user) > MAX_USER_CHARS:
            user = user[:MAX_USER_CHARS] + "\n[...truncated, posting was longer than the model's usable context]"

        payload = {
            "model": state.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": "json",
            "stream": False,
            "options": {"num_ctx": settings.ollama_num_ctx},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{state.base_url}/api/chat",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                # httpx's default error message doesn't include the response
                # body, which is exactly where Ollama puts the actual reason
                # for a 500 (OOM, context overflow, model crash, etc). Surface
                # it instead of a bare "500 Internal Server Error".
                body = exc.response.text[:500]
                if "out of memory" in body.lower() or "cudamalloc" in body.lower() or "failed to allocate" in body.lower():
                    raise RuntimeError(
                        f"Ollama ran out of GPU memory loading '{state.model}': {body}\n"
                        f"This is a GPU/driver-level allocation failure, not something JobRadar's "
                        f"request caused directly. A few things to try:\n"
                        f"  1. Run `ollama ps` to check whether another model is already loaded and "
                        f"holding VRAM — `ollama stop <model>` to free it, or set OLLAMA_MAX_LOADED_MODELS=1 "
                        f"before starting `ollama serve` so it doesn't try to keep multiple models resident.\n"
                        f"  2. Try `OLLAMA_FLASH_ATTENTION=true ollama serve` — flash attention meaningfully "
                        f"shrinks KV cache memory usage per token, and your config shows it's currently off.\n"
                        f"  3. Switch to a smaller chat model (JOBRADAR_OLLAMA_MODEL) if this GPU/driver combo "
                        f"can't comfortably fit this one alongside the embedding model."
                    ) from exc
                raise RuntimeError(
                    f"Ollama returned {exc.response.status_code} for model '{state.model}': {body or '(empty response body)'}\n"
                    f"Check the terminal running `ollama serve` for the underlying error — Ollama's own "
                    f"logs will usually show the real cause (out of memory, context length exceeded, etc). "
                    f"Also try the exact request directly: curl {state.base_url}/api/chat -d "
                    f'\'{{"model":"{state.model}","messages":[{{"role":"user","content":"hi"}}],"stream":false}}\''
                ) from exc
            except httpx.ConnectError as exc:
                raise RuntimeError(
                    f"Couldn't connect to Ollama at {state.base_url}. Is `ollama serve` actually "
                    f"running? Test it directly with: curl {state.base_url}/api/tags"
                ) from exc
            except httpx.TimeoutException as exc:
                raise RuntimeError(
                    f"Ollama at {state.base_url} didn't respond within 60s for model '{state.model}'. "
                    f"It may be overloaded, or the model may be too slow for this request on this hardware."
                ) from exc

            data = response.json()
            content = data["message"]["content"]
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Small/local models occasionally wrap JSON in prose despite the
                # format="json" constraint. Fall back to the canned shape rather
                # than surfacing a 500 to the frontend.
                return mock_response

    async def embed(self, text: str) -> list[float]:
        """
        Returns a vector embedding for the given text via Ollama's embeddings
        endpoint. In mock mode, returns a deterministic pseudo-embedding
        derived from a hash of the text so that identical or similar strings
        still produce comparable vectors during local dev without a real
        embedding model available.

        Tries the newer /api/embed endpoint first, falling back to the older
        /api/embeddings for older Ollama installs, since the shape differs
        slightly between versions.
        """
        if self.mock:
            return _mock_embedding(text)

        state = ollama_runtime.state
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        f"{state.base_url}/api/embed",
                        headers=self._headers(),
                        json={"model": state.embedding_model, "input": text},
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["embeddings"][0]
                except httpx.HTTPStatusError:
                    pass  # fall through to the older endpoint below

                try:
                    response = await client.post(
                        f"{state.base_url}/api/embeddings",
                        headers=self._headers(),
                        json={"model": state.embedding_model, "prompt": text},
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["embedding"]
                except httpx.HTTPStatusError as exc:
                    raise RuntimeError(
                        f"Ollama returned {exc.response.status_code} for embedding model "
                        f"'{state.embedding_model}' at {state.base_url}. Chat models (deepseek-r1, "
                        f"llama3.1, etc.) can't produce embeddings — you need a model built for it. "
                        f"Run `ollama pull {state.embedding_model}` (or set "
                        f"JOBRADAR_OLLAMA_EMBEDDING_MODEL to one you already have, e.g. "
                        f"mxbai-embed-large or all-minilm), then retry."
                    ) from exc
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"Couldn't connect to Ollama at {state.base_url}. Is `ollama serve` actually "
                f"running? Test it directly with: curl {state.base_url}/api/tags"
            ) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"Ollama at {state.base_url} didn't respond within 30s while embedding with "
                f"'{state.embedding_model}'. It may be overloaded or the model may be too slow "
                f"on this hardware."
            ) from exc

    async def health(self) -> bool:
        if self.mock:
            return True
        state = ollama_runtime.state
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{state.base_url}/api/tags", headers=self._headers())
                return response.status_code == 200
        except httpx.HTTPError:
            return False


def _mock_embedding(text: str) -> list[float]:
    """
    Deterministic bag-of-words-ish pseudo-embedding: hashes overlapping
    word shingles into fixed-size buckets so that texts sharing vocabulary
    produce vectors with nonzero cosine similarity, without needing a real
    model. This is a stand-in only — swap for a live embedding call once
    JOBRADAR_MOCK_LLM=false with a reachable Ollama instance.
    """
    vector = [0.0] * EMBEDDING_DIM
    words = text.lower().split()
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        bucket = struct.unpack("I", digest[:4])[0] % EMBEDDING_DIM
        vector[bucket] += 1.0
    norm = sum(v * v for v in vector) ** 0.5
    if norm > 0:
        vector = [v / norm for v in vector]
    return vector


ollama_client = OllamaClient()
