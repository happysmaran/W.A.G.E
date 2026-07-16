from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ollama connection. Local install defaults to localhost:11434 with no auth.
    # Cloud usage points OLLAMA_BASE_URL at https://ollama.com and requires OLLAMA_API_KEY.
    ollama_base_url: str = "http://localhost:11434"
    ollama_api_key: str | None = None
    ollama_model: str = "llama3.1:8b"
    # Chat models (deepseek-r1, llama3.1, gpt-oss, etc.) do not support the
    # embeddings endpoint — Ollama returns a 500 if you try. Embeddings need a
    # model actually built for it, e.g. nomic-embed-text or mxbai-embed-large.
    ollama_embedding_model: str = "nomic-embed-text"
    # Explicitly capping context length keeps the KV cache buffer Ollama
    # allocates small and predictable. Without this, Ollama picks its own
    # default (VRAM-based, but has been observed requesting far more than a
    # model this size should need — especially with flash attention off,
    # which meaningfully inflates KV cache memory per token). Our prompts
    # here are short (a job description plus a short system prompt), so a
    # modest context window is plenty and meaningfully lowers OOM risk on
    # tighter or less-mature GPU driver stacks (e.g. newer AMD ROCm cards).
    ollama_num_ctx: int = 2048

    # When true, the LLM and scraper calls are stubbed with deterministic canned
    # output instead of hitting a real Ollama instance or the network. This lets
    # the API run and be smoke-tested in environments with no Ollama installed.
    mock_llm: bool = False

    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_prefix = "JOBRADAR_"


settings = Settings()
