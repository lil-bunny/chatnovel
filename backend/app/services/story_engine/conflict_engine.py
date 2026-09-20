from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import PlotThread


def ensure_defaults(db: Session, story_id: str, names: list[str]) -> None:
    if db.query(PlotThread).filter_by(story_id=story_id).first():
        return
    db.add_all(
        [
            PlotThread(
                story_id=story_id,
                name="Unspoken attachment",
                description="Neither has directly confessed.",
                stakes="They may lose each other by staying polite.",
                involved_characters=names,
                severity=40,
            ),
            PlotThread(
                story_id=story_id,
                name="Family marriage pressure",
                description="A proposal conversation is forming around Maya.",
                stakes="A decision made for the family may close the door.",
                involved_characters=names,
                severity=35,
            ),
        ]
    )


def touch(db: Session, story_id: str, scene_id: str, beat: dict) -> list[str]:
    threads = db.query(PlotThread).filter_by(story_id=story_id, status="active").all()
    names = []
    if beat.get("reveal") and threads:
        threads[0].severity = min(100, threads[0].severity + 8)
        threads[0].last_touched_scene_id = scene_id
    for t in threads:
        names.append(t.name)
    return names
