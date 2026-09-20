# ChatNovel

Bengali chat fiction. FastAPI serves the HTML; the browser stores reading progress in `localStorage`. No database.

## Run locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000

Set `OPENAI_API_KEY` (or `LLM_API_KEY`) in `backend/.env`. On Render, add the same as an env var. Without a key, chapter 1 still plays from the canned story.

## Render

Repo root has `render.yaml`. In the dashboard:

- **Root directory:** `backend`
- **Build:** `pip install -r requirements.txt`
- **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Runtime:** Python 3.11
