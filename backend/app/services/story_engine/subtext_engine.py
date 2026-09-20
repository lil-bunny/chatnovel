from __future__ import annotations

from app.llm import LLMProvider
from app.llm import prompts


async def for_beat(provider: LLMProvider, beat: dict, characters: list[str], state: dict) -> list[dict]:
    user = f"Beat: {beat}\nCharacters: {characters}\nState: {state}"
    data = await provider.complete_json(prompts.SUBTEXT, user, cheap=True)
    lines = (data or {}).get("lines") or []
    if lines:
        return lines
    return [
        {
            "speaker": characters[0] if characters else "Deb",
            "literal_intent": "keep the conversation going",
            "hidden_intent": "see if the other person still chooses them",
            "fear": "being too obvious",
            "desired_response": "they stay",
        }
    ]
