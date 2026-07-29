import asyncio
import httpx
import trafilatura
from bs4 import BeautifulSoup

url = "https://boards.greenhouse.io/stripe/jobs/5238202"

async def main():
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
    html = resp.text
    
    text = trafilatura.extract(html, include_comments=False, include_tables=False)
    print("TRAFILATURA LENGTH:", len(text) if text else 0)
    print("TRAFILATURA PREVIEW:\n", text[:200] if text else "NONE")

    soup = BeautifulSoup(html, "html.parser")
    bs4_text = soup.get_text(separator="\n", strip=True)
    print("\nBS4 LENGTH:", len(bs4_text))
    print("BS4 PREVIEW:\n", bs4_text[:200])

asyncio.run(main())
