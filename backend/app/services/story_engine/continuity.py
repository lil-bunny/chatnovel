from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Memory, Story


def retrieve(db: Session, story_id: str, limit: int = 8) -> dict:
    story = db.get(Story, story_id)
    canonical = [m.content for m in db.query(Memory).filter_by(story_id=story_id, type="canonical").all()]
    events = (
        db.query(Memory)
        .filter_by(story_id=story_id, type="event")
        .order_by(Memory.importance.desc())
        .limit(limit)
        .all()
    )
    return {
        "bible": story.bible_json if story else {},
        "canonical": canonical,
        "events": [e.content for e in events],
    }


def remember_canon(db: Session, story_id: str, facts: list[str]) -> None:
    existing = {m.content for m in db.query(Memory).filter_by(story_id=story_id, type="canonical").all()}
    for fact in facts:
        if fact and fact not in existing:
            db.add(Memory(story_id=story_id, type="canonical", content=fact, importance=90))


def remember_event(db: Session, story_id: str, scene_id: str, summary: str, importance: int = 60) -> None:
    db.add(
        Memory(
            story_id=story_id,
            type="event",
            content=summary,
            source_scene_id=scene_id,
            importance=importance,
        )
    )
