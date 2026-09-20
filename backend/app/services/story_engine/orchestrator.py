from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.llm import get_provider
from app.models import Character, Chapter, CharacterEmotion, Message, Relationship, Scene, Story
from app.services.story_engine import conflict_engine, continuity, critic, dialogue_generator
from app.services.story_engine import emotion_engine, scene_director, subtext_engine
from app.services.story_engine.safety import SafetyError, post_check, pre_check


def current_state(db: Session, story: Story, chapter: Chapter) -> dict:
    rel = db.query(Relationship).filter_by(story_id=story.id).first()
    last_scene = (
        db.query(Scene)
        .join(Chapter)
        .filter(Chapter.story_id == story.id)
        .order_by(Scene.generated_at.desc())
        .first()
    )
    emotions = {}
    if last_scene:
        for row in last_scene.emotions:
            ch = db.get(Character, row.character_id)
            if ch:
                emotions[ch.name.lower()] = {
                    "affection": row.affection,
                    "trust": row.trust,
                    "longing": row.longing,
                    "fear": row.fear,
                    "jealousy": row.jealousy,
                    "pride": row.pride,
                    "vulnerability": row.vulnerability,
                    "frustration": row.frustration,
                    "hope": row.hope,
                    "resentment": row.resentment,
                    "age": ch.age,
                }
    else:
        for ch in story.characters:
            emotions[ch.name.lower()] = {
                "age": ch.age,
                "affection": 22,
                "trust": 34,
                "longing": 18,
                "fear": 36,
                "jealousy": 8,
                "pride": 55,
                "vulnerability": 20,
                "frustration": 12,
                "hope": 28,
                "resentment": 6,
            }
    return {
        "story_id": story.id,
        "chapter": chapter.chapter_number,
        "tension": int((chapter.outline_json or {}).get("escalation_target") or 30),
        "setting": (story.bible_json or {}).get("setting") or "Kolkata",
        "characters": emotions,
        "relationship": (rel.state_json if rel else {})
        or {
            "attraction": 28,
            "trust": 32,
            "emotional_intimacy": 18,
            "conflict": 14,
            "uncertainty": 40,
            "commitment": 12,
            "social_pressure": 24,
        },
    }


def recent_bodies(db: Session, story_id: str, n: int = 12) -> list[str]:
    rows = (
        db.query(Message)
        .join(Scene)
        .join(Chapter)
        .filter(Chapter.story_id == story_id, Message.kind == "text")
        .order_by(Message.message_index.desc())
        .limit(n)
        .all()
    )
    rows = list(reversed(rows))
    out = []
    for m in rows:
        name = m.character.name if m.character else "—"
        out.append(f"{name}: {m.body}")
    return out


def persist_messages(db: Session, scene: Scene, raw: list[dict], characters: list[Character]) -> list[Message]:
    by_name = {c.name.lower(): c for c in characters}
    start = len(scene.messages)
    saved = []
    for i, item in enumerate(raw):
        ch = by_name.get((item.get("speaker") or "").lower())
        msg = Message(
            scene_id=scene.id,
            character_id=ch.id if ch else None,
            message_index=start + i,
            body=item["body"],
            kind=item.get("kind") or "text",
            sent_at_story_time=item.get("sent_at_story_time"),
            metadata_json={"speaker": item.get("speaker")},
        )
        db.add(msg)
        saved.append(msg)
    db.flush()
    return saved


def persist_emotions(db: Session, scene: Scene, state: dict, characters: list[Character]) -> None:
    snapshot = state.get("characters") or {}
    for ch in characters:
        e = snapshot.get(ch.name.lower()) or {}
        db.add(
            CharacterEmotion(
                scene_id=scene.id,
                character_id=ch.id,
                affection=int(e.get("affection") or 0),
                trust=int(e.get("trust") or 0),
                longing=int(e.get("longing") or 0),
                fear=int(e.get("fear") or 0),
                jealousy=int(e.get("jealousy") or 0),
                pride=int(e.get("pride") or 0),
                vulnerability=int(e.get("vulnerability") or 0),
                frustration=int(e.get("frustration") or 0),
                hope=int(e.get("hope") or 0),
                resentment=int(e.get("resentment") or 0),
            )
        )
    chapter = db.get(Chapter, scene.chapter_id)
    rel = db.query(Relationship).filter_by(story_id=chapter.story_id).first() if chapter else None
    if rel:
        rel.state_json = state.get("relationship") or rel.state_json


async def generate_batch(db: Session, story: Story, chapter: Chapter) -> tuple[list[Message], dict]:
    characters = list(story.characters)
    pre_check(characters, story.blurb)
    provider = get_provider()
    memory = continuity.retrieve(db, story.id)
    state = current_state(db, story, chapter)
    recent = recent_bodies(db, story.id)
    threads = [t.name for t in story.plot_threads if t.status == "active"]
    context = {
        "bible": memory["bible"] or story.bible_json,
        "chapter_plan": chapter.outline_json,
        "state": state,
        "recent": recent,
        "threads": threads,
    }
    beat = await scene_director.direct(provider, context)
    state = emotion_engine.apply_deltas(state, beat.get("emotional_shift") or {}, major_reveal=bool(beat.get("reveal")))
    if "tension_delta" in beat:
        state["tension"] = emotion_engine.clamp(int(state.get("tension") or 0) + int(beat["tension_delta"]))

    scene = (
        db.query(Scene)
        .filter_by(chapter_id=chapter.id)
        .order_by(Scene.sequence_number.desc())
        .first()
    )
    next_seq = (scene.sequence_number + 1) if scene else 1
    # Continue last scene if it is still short; otherwise open a new one.
    if scene and len(scene.messages) < 8 and not beat.get("cliffhanger"):
        active = scene
    else:
        active = Scene(
            chapter_id=chapter.id,
            sequence_number=next_seq,
            scene_state_json=beat,
            generated_at=datetime.now(timezone.utc),
        )
        db.add(active)
        db.flush()

    subtext = await subtext_engine.for_beat(provider, beat, [c.name for c in characters], state)
    payload = {
        "characters": [
            {"name": c.name, "age": c.age, "speech": c.speech_style_json, "personality": c.personality_json}
            for c in characters
        ],
        "scene_goal": beat.get("scene_goal"),
        "subtext": subtext,
        "recent": recent,
    }

    last_error = None
    raw: list[dict] = []
    for _ in range(settings.critic_max_retries + 1):
        raw = await dialogue_generator.generate(provider, payload)
        try:
            post_check([m["body"] for m in raw])
        except SafetyError as e:
            last_error = e
            payload["recent"] = recent + [f"SAFETY REPAIR: {e}"]
            continue
        verdict = await critic.review(provider, raw, story.bible_json, recent, characters)
        if verdict["pass"]:
            break
        last_error = ValueError(verdict["repair_instruction"] or "critic failed")
        payload["recent"] = recent + [f"REPAIR: {verdict['repair_instruction']}"]
    else:
        if last_error:
            raise last_error

    saved = persist_messages(db, active, raw, characters)
    persist_emotions(db, active, state, characters)
    active.summary = beat.get("next_event") or beat.get("scene_goal") or ""
    active.scene_state_json = {**beat, "tension": state.get("tension")}
    conflict_engine.touch(db, story.id, active.id, beat)
    continuity.remember_event(db, story.id, active.id, active.summary, importance=70 if beat.get("reveal") else 50)

    if beat.get("cliffhanger") or len(chapter.scenes) >= 3:
        chapter.status = "complete"
    else:
        chapter.status = "ready"

    db.flush()
    return saved, beat
