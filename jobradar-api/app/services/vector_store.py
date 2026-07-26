from __future__ import annotations

import numpy as np

from app.services.ollama_client import ollama_client


def _cosine(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if denom == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


class ResumeVectorIndex:
    """In-memory embedding index with cosine similarity.

    Stand-in for a real vector DB (Qdrant/ChromaDB). Swap the storage/search
    internals here and nothing in services/scoring.py needs to change.
    """

    def __init__(self) -> None:
        # persona_id -> list of {"section", "text", "embedding"}
        self._chunks: dict[str, list[dict]] = {}

    async def index_resume(self, persona_id: str, chunks: list[dict]) -> None:
        embedded = []
        for chunk in chunks:
            vector = await ollama_client.embed(chunk["text"])
            embedded.append({"section": chunk["section"], "text": chunk["text"], "embedding": vector})
        self._chunks[persona_id] = embedded

    def remove_persona(self, persona_id: str) -> None:
        self._chunks.pop(persona_id, None)

    async def best_matches(self, persona_id: str, job_text: str, top_k: int = 5) -> list[tuple[dict, float]]:
        chunks = self._chunks.get(persona_id, [])
        if not chunks:
            return []

        job_vector = await ollama_client.embed(job_text)
        scored = [
            ({"section": c["section"], "text": c["text"]}, _cosine(c["embedding"], job_vector))
            for c in chunks
        ]
        return sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]

    async def overall_similarity(self, persona_id: str, job_text: str) -> float:
        chunks = self._chunks.get(persona_id, [])
        matches = await self.best_matches(persona_id, job_text, top_k=len(chunks) or 1)
        if not matches:
            return 0.0
        scores = [score for _, score in matches]
        return float(np.mean(scores)) if scores else 0.0


vector_index = ResumeVectorIndex()
