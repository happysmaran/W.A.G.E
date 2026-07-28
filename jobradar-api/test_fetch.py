import asyncio
from app.services.job_discovery import job_discovery_client
from app.services.runtime_config import runtime_config

async def main():
    runtime_config.state.mock_llm = False # force real fetch
    # using dummy api_key to bypass the check, it might fail ollama fetch and fall back to playwright
    runtime_config.state.api_key = "dummy"
    url = "https://boards.greenhouse.io/demandbase/jobs/4568603005"
    try:
        content = await job_discovery_client.fetch(url)
        print("LENGTH:", len(content))
        print("PREVIEW:", content[:500])
    except Exception as e:
        print("ERROR:", e)

asyncio.run(main())
