from __future__ import annotations

from app.llm import LLMProvider
from app.llm import prompts


async def generate(provider: LLMProvider, payload: dict) -> list[dict]:
    user = (
        f"Character profiles: {payload.get('characters')}\n"
        f"Scene objective: {payload.get('scene_goal')}\n"
        f"Subtext: {payload.get('subtext')}\n"
        f"Recent chat: {payload.get('recent')}\n"
        f"Language: Bengali\nDo not invent new backstory."
    )
    data = await provider.complete_json(prompts.DIALOGUE, user)
    messages = (data or {}).get("messages") or []
    cleaned = []
    for m in messages:
        body = (m.get("body") or "").strip()
        if not body:
            continue
        cleaned.append(
            {
                "speaker": m.get("speaker") or "Deb",
                "body": body,
                "kind": m.get("kind") or "text",
                "sent_at_story_time": m.get("sent_at_story_time"),
            }
        )
    return cleaned[:10]
