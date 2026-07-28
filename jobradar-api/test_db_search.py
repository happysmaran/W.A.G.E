import asyncio
from sqlmodel import Session, select
from app.db import engine
from app.models.db_models import SettingsDB
from app.services.runtime_config import runtime_config
from app.services.job_discovery import job_discovery_client

async def main():
    # Load settings from DB exactly as backend does
    with Session(engine) as session:
        row = session.exec(select(SettingsDB)).first()
        if row:
            runtime_config.update(
                mode=row.mode,
                model=row.model,
                embedding_model=row.embedding_model,
                base_url=row.base_url,
                api_key=row.api_key,
                num_ctx=row.num_ctx,
                mock_llm=row.mock_llm,
                mock_scraper=row.mock_scraper,
            )
            print("Loaded API key:", "***" if row.api_key else "None")

    runtime_config.state.mock_llm = False 

    try:
        results = await job_discovery_client.search("backend intern remote", max_results=2)
        print("SUCCESS:", results)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
