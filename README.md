# W.A.G.E

W.A.G.E (Work Aggregation and Guidance Engine) is a local-first job search strategy tool: upload your resume, paste job postings, get an explainable fit score, a tailored resume bullet, and a first-draft outreach message, all powered by a local (or cloud) Ollama model.

## Structure

- **`/`** — Next.js 14 + TypeScript + Tailwind frontend
- **`/jobradar-api/`** — Python + FastAPI + SQLModel backend

## Running it

```bash
# Terminal 1 - backend
cd jobradar-api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 - frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Keep in mind Ollama is required to actually use AI models with this, but you can run this in a 'test' mode using the `mock_llm` parameter in main.py inside of the api folder.

## Using an AI model

1. Install [Ollama](https://ollama.com), then pull two models — one for chat/reasoning, one for embeddings:
   ```bash
   ollama pull llama3.1:8b
   ollama pull nomic-embed-text
   ```
2. In the app: gear icon (top bar) → Settings → toggle Mock mode off, confirm the base URL and model names. Changes apply immediately, no restart needed.

Embedding models and chat models are not interchangeable; chat models (`deepseek-r1`, `llama3.1`, etc.) will error if used for embeddings.

## How to use

1. **Upload a resume** (sidebar -> *+ Add persona*) - extracted, chunked, and embedded for similarity scoring.
2. **Paste a job posting** (*+ Add job*) - cleaned up automatically (nav menus, cookie banners, etc. stripped) and scored against your resume.
3. **Review the score breakdown** in the Battle Room - concrete matches and gaps, not just a number.
4. **Generate** a tailored resume bullet and a first-draft outreach message - both editable before you use them anywhere.
5. **Track status** (Inbox -> Reviewing -> Applied -> Archived) and delete what you don't need.

## Known Limitations

- **No automated job-board scraping.** Tried and removed - Unfortunately, API results were inconsistent, JS-rendered career pages needed a full headless browser for fragile payoff, and scraping sits in a legal grey area regardless. Paste-and-clean is the one ingestion path.
- **No auth/multi-user support.** Single-desk tool; mainly because every persona/job would be globally visible to whoever's running the backend. So no server is provided by me as a result.
- **No production-grade vector DB.** In-memory cosine similarity stands in for Qdrant/ChromaDB, which is fine at personal scale.

See the backend's sub README for more info.

(note that this software was originally called 'jobradar' so you may see it being referenced as that somewhere.)