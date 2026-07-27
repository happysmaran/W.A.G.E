from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-variable defaults, used to seed runtime_config at startup.

    After startup, settings are mutable via the /settings API (see
    services/runtime_config.py) and persisted to the DB — these env vars
    only matter for the very first run, or after clearing WAGE.db.
    """

    ollama_base_url: str = "http://localhost:11434"
    ollama_api_key: str | None = None
    ollama_model: str = "llama3.1:8b"
    ollama_num_ctx: int = 4096
    mock_llm: bool = False

    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_prefix = "WAGE_"


settings = Settings()
