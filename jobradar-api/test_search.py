import asyncio
from app.services.job_discovery import job_discovery_client
from app.services.runtime_config import runtime_config

async def main():
    runtime_config.state.mock_llm = False 
    try:
        # Assuming the user has an API key configured in their environment or DB,
        # but if we run this script directly it might not have the DB state.
        # Let's just try running the exact code in job_discovery.py to see if there's a syntax/type error.
        results = await job_discovery_client.search("backend intern remote", max_results=2)
        print("SUCCESS", results)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
