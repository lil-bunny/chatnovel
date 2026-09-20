from sqlalchemy.orm import Session

from app.auth_utils import hash_password
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import (
    Chapter,
    Character,
    CharacterEmotion,
    Message,
    PlotThread,
    Relationship,
    Scene,
    Story,
    User,
)
from app.seed_story import BIBLE, CHAPTERS, THREADS
from app.services.story_engine import conflict_engine, continuity


def seed(db: Session) -> None:
    if db.query(User).filter_by(email=settings.admin_email).first():
        return
    user = User(
        email=settings.admin_email,
        password_hash=hash_password("demo1234"),
        is_admin=True,
        language="bn",
    )
    db.add(user)

    story = Story(
        title="যা বলা হয়নি",
        slug="ja-bola-hoyni",
        language="bn",
        genre="romance",
        blurb="কলকাতার দুই প্রাপ্তবয়স্ক মানুষ, একটা আড্ডার পরিচয়, আর যে কথাটা মুখে আসে না। পরিবারের চাপ বাড়ে। পাঠক শুধু তাদের চ্যাট দেখেন।",
        status="published",
        target_chapters=10,
        age_rating="18+",
        bible_json=BIBLE,
        free_chapter_count=settings.free_chapter_count,
        cover_url=None,
    )
    db.add(story)
    db.flush()

    maya = Character(
        story_id=story.id,
        name="Maya",
        age=24,
        pronouns="she/her",
        role="lead",
        personality_json=BIBLE["characters"][0]["personality"],
        speech_style_json=BIBLE["characters"][0]["speech_style"],
        goals_json=BIBLE["characters"][0]["goals"],
        fears_json=BIBLE["characters"][0]["fears"],
        secrets_json=BIBLE["characters"][0]["secrets"],
        avatar_hue=338,
    )
    arjun = Character(
        story_id=story.id,
        name="Arjun",
        age=26,
        pronouns="he/him",
        role="lead",
        personality_json=BIBLE["characters"][1]["personality"],
        speech_style_json=BIBLE["characters"][1]["speech_style"],
        goals_json=BIBLE["characters"][1]["goals"],
        fears_json=BIBLE["characters"][1]["fears"],
        secrets_json=BIBLE["characters"][1]["secrets"],
        avatar_hue=198,
    )
    db.add_all([maya, arjun])
    db.flush()
    by_name = {"maya": maya, "arjun": arjun}

    db.add(
        Relationship(
            story_id=story.id,
            character_a_id=maya.id,
            character_b_id=arjun.id,
            state_json={
                "attraction": 74,
                "trust": 61,
                "emotional_intimacy": 58,
                "conflict": 49,
                "uncertainty": 62,
                "commitment": 40,
                "social_pressure": 81,
            },
        )
    )
    for t in THREADS:
        db.add(
            PlotThread(
                story_id=story.id,
                name=t["name"],
                description=t["description"],
                stakes=t["stakes"],
                involved_characters=["Maya", "Arjun"],
                severity=t["severity"],
            )
        )
    continuity.remember_canon(
        db,
        story.id,
        [
            BIBLE["premise"],
            "Maya is 24. Arjun is 26.",
            "Neither has directly confessed.",
            "Maya's family is discussing a marriage proposal.",
        ],
    )

    emotion_ladders = [
        (22, 34, 18, 36, 55, 20, 28),
        (30, 40, 28, 34, 52, 26, 34),
        (42, 52, 40, 38, 48, 44, 46),
        (48, 50, 52, 58, 60, 40, 40),
        (58, 56, 68, 54, 50, 55, 48),
        (60, 48, 74, 70, 66, 50, 36),
        (55, 40, 70, 62, 72, 38, 22),
        (68, 58, 80, 60, 48, 62, 55),
        (76, 70, 86, 72, 42, 74, 60),
        (82, 78, 88, 58, 36, 80, 70),
    ]

    for ch, ladder in zip(CHAPTERS, emotion_ladders):
        chapter = Chapter(
            story_id=story.id,
            chapter_number=ch["n"],
            title=ch["title"],
            outline_json={
                "objective": ch["objective"],
                "emotional_objective": ch["emotional_objective"],
                "escalation_target": ch["escalation_target"],
                "cliffhanger": ch["closing"],
                "closing_line": ch["closing"],
            },
            status="complete",
            closing_line=ch["closing"],
        )
        db.add(chapter)
        db.flush()
        scene = Scene(
            chapter_id=chapter.id,
            sequence_number=1,
            summary=ch["objective"],
            scene_state_json={"tension": ch["escalation_target"]},
        )
        db.add(scene)
        db.flush()
        for i, m in enumerate(ch["messages"]):
            speaker = m.get("speaker")
            db.add(
                Message(
                    scene_id=scene.id,
                    character_id=by_name[speaker.lower()].id if speaker else None,
                    message_index=i,
                    body=m["body"],
                    kind=m.get("kind") or "text",
                    sent_at_story_time=None,
                    metadata_json={"speaker": speaker} if speaker else {},
                )
            )
        aff, trust, longing, fear, pride, vuln, hope = ladder
        for person, bias in ((maya, 0), (arjun, 2)):
            db.add(
                CharacterEmotion(
                    scene_id=scene.id,
                    character_id=person.id,
                    affection=aff + bias,
                    trust=trust,
                    longing=longing + bias,
                    fear=fear,
                    pride=pride,
                    vulnerability=vuln,
                    hope=hope,
                    jealousy=8 + ch["n"],
                    frustration=10 + ch["n"],
                    resentment=4 + ch["n"] // 2,
                )
            )
        continuity.remember_event(db, story.id, scene.id, ch["objective"], importance=50 + ch["n"])

    conflict_engine.ensure_defaults(db, story.id, ["Maya", "Arjun"])
    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        seed(session)
        print("Seeded demo@chatnovel.local / demo1234 and story যা বলা হয়নি")
    finally:
        session.close()
