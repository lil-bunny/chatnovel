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
        f"era_rules: {context.get('era_rules')}\n"
        "Place Deb and Visha. Select the next scene beat. Do not write their lines."
    )
    rules = context.get("era_rules") or {}
    sys = (
        prompts.JANITOR_SCENE
        if rules.get("channel") == "chat" and rules.get("heat") == "erotic"
        else prompts.SCENE_DIRECTOR
    )
    beat = await provider.complete_json(sys, user)
    return beat or heuristic_beat(context)


def heuristic_beat(context: dict) -> dict:
    chapter = context.get("chapter_plan") or {}
    tension = int((context.get("state") or {}).get("tension") or 30)
    target = int(chapter.get("escalation_target") or 50)
    delta = max(-8, min(8, target - tension))
    return {
        "scene_goal": chapter.get("objective") or "Move the relationship one inch forward.",
        "next_event": chapter.get("reveal") or "A withheld fact almost surfaces.",
        "slugline": "দৃশ্য · উঠোন · সন্ধ্যা",
        "blocking": "Deb waits apart; Visha is just out of easy view.",
        "action": "A folded note changes hands. Neither looks up long.",
        "emotional_shift": {"longing": 3, "fear": 2 if delta > 0 else -1, "relationship_tension": delta},
        "reveal": tension > 55,
        "cliffhanger": tension >= int(chapter.get("escalation_target") or 80),
        "tension_delta": delta,
    }
