from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth_utils import admin_user
from app.db import get_db
from app.llm import get_provider
from app.models import Chapter, Relationship, Story, User
from app.schemas import StoryBriefIn, StoryOut
from app.services.story_engine import chapter_planner, conflict_engine, continuity, story_bible
from app.services.story_engine.orchestrator import generate_batch
from app.api.stories import story_to_out

router = APIRouter(prefix="/v1/admin", tags=["admin"])


def slugify(title: str) -> str:
    raw = "".join(ch.lower() if ch.isalnum() else "-" for ch in title).strip("-")
    return raw[:48] or "story"


@router.post("/stories", response_model=StoryOut)
async def create_story(body: StoryBriefIn, db: Session = Depends(get_db), _: User = Depends(admin_user)):
    provider = get_provider()
    bible = await story_bible.build_bible(provider, body.model_dump())
    story = Story(
        title=body.title,
        slug=slugify(body.title),
        language="bn",
        genre=body.genre,
        blurb=body.blurb,
        status="published",
        target_chapters=body.target_chapters,
        bible_json=bible,
    )
    db.add(story)
    db.flush()
    chars = story_bible.persist_bible(story, bible)
    db.add_all(chars)
    db.flush()
    if len(chars) >= 2:
        db.add(
            Relationship(
                story_id=story.id,
                character_a_id=chars[0].id,
                character_b_id=chars[1].id,
                state_json={"attraction": 20, "trust": 25, "conflict": 10, "social_pressure": 20},
            )
        )
    conflict_engine.ensure_defaults(db, story.id, [c.name for c in chars])
    continuity.remember_canon(
        db,
        story.id,
        [bible.get("premise") or body.blurb] + [f"{c.name} is {c.age}" for c in chars],
    )
    return story_to_out(story)


@router.post("/stories/{story_id}/generate-outline")
async def generate_outline(story_id: str, db: Session = Depends(get_db), _: User = Depends(admin_user)):
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    plans = await chapter_planner.plan_chapters(get_provider(), story.bible_json, story.target_chapters)
    db.query(Chapter).filter_by(story_id=story.id).delete()
    for plan in plans:
        db.add(
            Chapter(
                story_id=story.id,
                chapter_number=int(plan["chapter_number"]),
                title=plan.get("title") or f"Chapter {plan['chapter_number']}",
                outline_json=plan,
                closing_line=plan.get("closing_line") or "",
                status="draft",
            )
        )
    db.flush()
    return {"chapters": len(plans)}


@router.post("/stories/{story_id}/generate-chapter")
async def generate_chapter(story_id: str, chapter_id: str, db: Session = Depends(get_db), _: User = Depends(admin_user)):
    story = db.get(Story, story_id)
    chapter = db.get(Chapter, chapter_id)
    if not story or not chapter:
        raise HTTPException(404, "Not found")
    messages, beat = await generate_batch(db, story, chapter)
    return {"generated": len(messages), "beat": beat}


@router.post("/stories/{story_id}/regenerate-scene")
async def regenerate_scene(story_id: str, chapter_id: str, db: Session = Depends(get_db), _: User = Depends(admin_user)):
    return await generate_chapter(story_id, chapter_id, db, _)


@router.get("/stories/{story_id}/state")
def admin_state(story_id: str, db: Session = Depends(get_db), _: User = Depends(admin_user)):
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    return {
        "bible": story.bible_json,
        "characters": [{"name": c.name, "age": c.age, "secrets": c.secrets_json} for c in story.characters],
        "threads": [{"name": t.name, "status": t.status, "severity": t.severity} for t in story.plot_threads],
        "chapters": [{"id": c.id, "n": c.chapter_number, "title": c.title, "status": c.status} for c in story.chapters],
    }
