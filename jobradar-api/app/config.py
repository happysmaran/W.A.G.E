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

    # Job-feed poller (see services/job_feed.py). Feeds pull from public ATS
    # board APIs (Greenhouse/Lever/Ashby) on a timer; new postings are staged
    # for review, never auto-imported.
    mock_scraper: bool = False
    feed_poll_interval_seconds: int = 1800  # 30 min
    feed_poll_enabled: bool = True

    # The packaged Electron app serves the UI from a locally-spawned
    # http server on a random 127.0.0.1 port (see main.js), so we can't
    # pin an exact origin the way we can for `next dev`. No cookies/
    # credentials are used by lib/api.ts, so a wildcard is safe here.
    cors_origins: list[str] = ["http://localhost:3000", "*"]

    class Config:
        env_prefix = "WAGE_"


settings = Settings()