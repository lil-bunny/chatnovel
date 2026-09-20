from __future__ import annotations

from app.llm import LLMProvider
from app.llm import prompts
from app.models import Character, Story
from app.services.story_engine.safety import pre_check


async def build_bible(provider: LLMProvider, brief: dict) -> dict:
    chars = brief.get("characters") or []
    for c in chars:
        age = int(c.get("age") or 0)
        if age < 18:
            raise ValueError("All romantic characters must be 18+")
    user = (
        f"Title: {brief.get('title')}\nGenre: {brief.get('genre')}\n"
        f"Setting: {brief.get('setting')}\nChapters: {brief.get('target_chapters')}\n"
        f"Blurb: {brief.get('blurb')}\nDirection: {brief.get('literary_direction')}\n"
        f"Characters: {chars}"
    )
    data = await provider.complete_json(prompts.STORY_BIBLE, user)
    if not data:
        data = _fallback_bible(brief)
    return data


def persist_bible(story: Story, bible: dict, CharacterCls=Character) -> list[Character]:
    story.bible_json = bible
    created = []
    for spec in bible.get("characters") or []:
        created.append(
            CharacterCls(
                story_id=story.id,
                name=spec["name"],
                age=int(spec["age"]),
                pronouns=spec.get("pronouns") or "they/them",
                role=spec.get("role") or "lead",
                personality_json=spec.get("personality") or {},
                speech_style_json=spec.get("speech_style") or {},
                goals_json=spec.get("goals") or [],
                fears_json=spec.get("fears") or [],
                secrets_json=spec.get("secrets") or [],
            )
        )
    pre_check(created, story.blurb)
    return created


def _fallback_bible(brief: dict) -> dict:
    chars = brief.get("characters") or [
        {"name": "Maya", "age": 24, "pronouns": "she/her", "role": "lead"},
        {"name": "Arjun", "age": 26, "pronouns": "he/him", "role": "lead"},
    ]
    return {
        "premise": brief.get("blurb") or "Two adults in Kolkata grow close under family pressure.",
        "setting": brief.get("setting") or "Kolkata",
        "timeline_anchors": ["present-day late monsoon"],
        "locations": ["Kolkata apartments", "late-night chat"],
        "characters": [
            {
                "name": c["name"],
                "age": int(c["age"]),
                "pronouns": c.get("pronouns") or "they/them",
                "role": c.get("role") or "lead",
                "personality": {"restraint": "high"},
                "speech_style": {"length": "short", "subtext": "strong"},
                "goals": ["be understood without having to explain everything"],
                "fears": ["family disappointment", "being too late"],
                "secrets": ["has not said what they want"],
                "backstory": c.get("backstory") or "",
            }
            for c in chars
        ],
        "relationships": [],
        "social_context": "Bengali urban middle-class family expectation around marriage.",
    }
