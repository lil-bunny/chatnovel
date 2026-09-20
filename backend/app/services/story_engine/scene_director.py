from __future__ import annotations

from app.llm import LLMProvider
from app.llm import prompts


async def direct(provider: LLMProvider, context: dict) -> dict:
    user = (
        f"Story Bible: {context.get('bible')}\n"
        f"Chapter plan: {context.get('chapter_plan')}\n"
        f"Current state: {context.get('state')}\n"
        f"Recent messages: {context.get('recent')}\n"
        f"Open threads: {context.get('threads')}\n"
        "Select the next scene beat."
    )
    beat = await provider.complete_json(prompts.SCENE_DIRECTOR, user)
    return beat or heuristic_beat(context)


def heuristic_beat(context: dict) -> dict:
    chapter = context.get("chapter_plan") or {}
    tension = int((context.get("state") or {}).get("tension") or 30)
    target = int(chapter.get("escalation_target") or 50)
    delta = max(-8, min(8, target - tension))
    return {
        "scene_goal": chapter.get("objective") or "Move the relationship one inch forward.",
        "next_event": chapter.get("reveal") or "A withheld fact almost surfaces.",
        "emotional_shift": {"longing": 3, "fear": 2 if delta > 0 else -1, "relationship_tension": delta},
        "reveal": tension > 55,
        "cliffhanger": tension >= int(chapter.get("escalation_target") or 80),
        "tension_delta": delta,
    }
