from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.generate import next_batch
from app.plot import compose, presets
from app.seed_story import BIBLE, CHAPTERS

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="ChatNovel", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class GenerateIn(BaseModel):
    chapter: int = 0
    already: int = 0
    recent: list[dict] = Field(default_factory=list)
    tension: int = 0
    bible: dict | None = None
    chapters: list[dict] | None = None
    era_rules: dict | None = None


class PlotIn(BaseModel):
    trope: str = "slow_burn"
    era: str = "calcutta_1850"


@app.get("/health")
def health():
    return {"ok": True, "product": "chatnovel", "llm": bool(settings.api_key)}


@app.get("/v1/presets")
def list_presets():
    return presets()


@app.post("/v1/plot")
async def plot(body: PlotIn):
    try:
        return await compose(body.trope, body.era)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/v1/story")
def story():
    return {
        "title": "যা বলা হয়নি",
        "blurb": "১৮৫০, কলকাতা। Deb আর Visha-এর গোপন চিঠি।",
        "first_person": "Deb",
        "second_person": "Visha",
        "llm": bool(settings.api_key),
        "bible": BIBLE,
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
        "era_rules": {
            "era": "calcutta_1850",
            "channel": "notes",
        },
    }


@app.post("/v1/generate")
async def generate(body: GenerateIn):
    pack = {}
    if body.bible:
        pack["bible"] = body.bible
    if body.chapters:
        pack["chapters"] = body.chapters
    if body.era_rules:
        pack["era_rules"] = body.era_rules
    n = len(pack.get("chapters") or CHAPTERS)
    idx = max(0, min(body.chapter, n - 1))
    return await next_batch(idx, body.recent, body.already, body.tension, pack or None)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
