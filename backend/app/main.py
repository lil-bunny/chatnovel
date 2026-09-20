from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.generate import next_batch
from app.seed_story import BIBLE, CHAPTERS

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="ChatNovel", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class GenerateIn(BaseModel):
    chapter: int = 0
    already: int = 0
    recent: list[dict] = Field(default_factory=list)
    tension: int = 0


@app.get("/health")
def health():
    return {"ok": True, "product": "chatnovel", "llm": bool(settings.api_key)}


@app.get("/v1/story")
def story():
    return {
        "title": "যা বলা হয়নি",
        "blurb": "১৮৫০, কলকাতা। Deb আর Visha-এর গোপন চিঠি।",
        "first_person": "Deb",
        "second_person": "Visha",
        "llm": bool(settings.api_key),
        "characters": BIBLE["characters"],
        "chapters": [
            {
                "n": c["n"],
                "title": c["title"],
                "closing": c["closing"],
                "objective": c["objective"],
                "messages": [] if settings.api_key else c["messages"],
            }
            for c in CHAPTERS
        ],
    }


@app.post("/v1/generate")
async def generate(body: GenerateIn):
    idx = max(0, min(body.chapter, len(CHAPTERS) - 1))
    return await next_batch(idx, body.recent, body.already, body.tension)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
