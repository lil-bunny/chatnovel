from __future__ import annotations

from app.llm import LLMProvider
from app.llm import prompts


def _names(characters) -> set[str]:
    out = set()
    for c in characters or []:
        out.add(str(getattr(c, "name", c) or "").lower())
    return out


async def review(
    provider: LLMProvider,
    messages: list[dict],
    bible: dict,
    recent: list[str],
    characters: list,
) -> dict:
    heuristic = heuristic_review(messages, bible, characters)
    if not heuristic["pass"]:
        return heuristic
    data = await provider.complete_json(
        prompts.CRITIC,
        f"Bible: {bible}\nRecent: {recent}\nNew messages: {messages}",
        cheap=True,
    )
    if not data:
        return heuristic
    return {
        "pass": bool(data.get("pass")),
        "issues": data.get("issues") or [],
        "repair_instruction": data.get("repair_instruction") or "",
    }


def heuristic_review(messages: list[dict], bible: dict, characters: list) -> dict:
    issues = []
    names = _names(characters)
    if not messages:
        issues.append("No messages generated")
    for m in messages:
        if (m.get("kind") or "text") not in ("text",):
            continue
        speaker = (m.get("speaker") or "").lower()
        if speaker and speaker not in names:
            issues.append(f"Unknown speaker {m.get('speaker')}")
    bodies = " ".join(m.get("body") or "" for m in messages)
    if bodies.lower().count("i love you") + bodies.count("আমি তোমায় ভালোবাসি") > 2:
        issues.append("Repetitive confession loop")
    return {"pass": not issues, "issues": issues, "repair_instruction": "; ".join(issues)}
