from __future__ import annotations

import json

import httpx

from app.services.runtime_config import runtime_config

MAX_USER_CHARS = 6000


class OllamaClient:
    """Wrapper around Ollama's /api/chat endpoint (local or cloud).

    Embeddings are NOT handled here — Ollama's cloud API has no embedding
    models (chat-only), so embeddings live in services/embedding_client.py
    as a separate, mode-independent, in-process path. This client only
    ever needs to talk to Ollama for chat/scoring, in either mode.

    Reads connection details from runtime_config on every call, so changes
    made via the settings API take effect immediately with no restart.
    """

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if runtime_config.state.api_key:
            headers["Authorization"] = f"Bearer {runtime_config.state.api_key}"
        return headers

    async def chat_json(self, system: str, user: str, mock_response: dict) -> dict:
        if runtime_config.state.mock_llm:
            return mock_response

        state = runtime_config.state
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
            "options": {"num_ctx": state.num_ctx},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(f"{state.base_url}/api/chat", headers=self._headers(), json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                body = exc.response.text[:500]
                if any(s in body.lower() for s in ("out of memory", "cudamalloc", "failed to allocate")):
                    raise RuntimeError(
                        f"Ollama ran out of GPU memory loading '{state.model}': {body}\n"
                        f"This is a GPU/driver-level allocation failure, not something WAGE's "
                        f"request caused directly. A few things to try:\n"
                        f"  1. `ollama ps` to check whether another model is already loaded and holding "
                        f"VRAM — `ollama stop <model>` to free it, or set OLLAMA_MAX_LOADED_MODELS=1.\n"
                        f"  2. Try `OLLAMA_FLASH_ATTENTION=true ollama serve` — this meaningfully shrinks "
                        f"KV cache memory per token.\n"
                        f"  3. Switch to a smaller chat model if this GPU/driver combo can't fit this one."
                    ) from exc
                raise RuntimeError(
                    f"Ollama returned {exc.response.status_code} for model '{state.model}': "
                    f"{body or '(empty response body)'}\n"
                    f"Check the terminal running `ollama serve` for the underlying error."
                ) from exc
            except httpx.ConnectError as exc:
                raise RuntimeError(
                    f"Couldn't connect to Ollama at {state.base_url}. Is `ollama serve` running? "
                    f"Test directly with: curl {state.base_url}/api/tags"
                ) from exc
            except httpx.TimeoutException as exc:
                raise RuntimeError(
                    f"Ollama at {state.base_url} didn't respond within 60s for model '{state.model}'."
                ) from exc

            content = response.json()["message"]["content"]
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Some models wrap JSON in prose despite format="json". Fall
                # back to the canned shape rather than surfacing a 500.
                return mock_response

    async def health(self) -> bool:
        if runtime_config.state.mock_llm:
            return True
        state = runtime_config.state
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{state.base_url}/api/tags", headers=self._headers())
                return response.status_code == 200
        except httpx.HTTPError:
            return False


ollama_client = OllamaClient()
