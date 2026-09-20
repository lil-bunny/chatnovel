from __future__ import annotations

from typing import Any

from app.config import settings
from app.llm import LLMProvider, get_provider
from app.llm import prompts
from app.seed_story import BIBLE, CHAPTERS, THREADS
from app.services.story_engine import critic, emotion_engine, scene_director, subtext_engine
from app.services.story_engine.safety import SafetyError, post_check

FIRST = "Deb"
SECOND = "Visha"
LEADS = [FIRST, SECOND]


def _canned(chapter: dict, already: int) -> dict[str, Any]:
    raw = chapter["messages"][already : already + 8]
    msgs = []
    for m in raw:
        sp = m.get("speaker")
        if sp == "Maya":
            sp = FIRST
        elif sp == "Arjun":
            sp = SECOND
        msgs.append({**m, "speaker": sp})
    return {
        "messages": msgs,
        "chapter_complete": already + len(msgs) >= len(chapter["messages"]),
        "closing": chapter["closing"],
        "llm": False,
        "tension": int(chapter.get("escalation_target") or 0),
    }


def _state(chapter: dict, already: int, tension: int) -> dict:
    t = tension or min(100, 18 + already * 3)
    return {
        "tension": t,
        "setting": "Calcutta, 1850",
        "chapter": chapter.get("n"),
        "already": already,
        "characters": {
            "deb": {"pride": 55, "fear": 40, "longing": 20, "affection": 22, "trust": 34, "vulnerability": 20, "hope": 28, "frustration": 12, "jealousy": 8, "resentment": 6},
            "visha": {"pride": 48, "fear": 44, "longing": 22, "affection": 24, "trust": 36, "vulnerability": 28, "hope": 30, "frustration": 14, "jealousy": 6, "resentment": 8},
        },
        "relationship": {
            "attraction": 28,
            "trust": 32,
            "emotional_intimacy": 18,
            "conflict": 14,
            "uncertainty": 40,
            "commitment": 12,
            "social_pressure": 24 + already,
        },
    }


def _recent_lines(recent: list[dict]) -> list[str]:
    lines = []
    for m in recent[-16:]:
        who = m.get("speaker") or ""
        body = (m.get("body") or "").strip()
        if body:
            lines.append(f"{who}: {body}".strip(": "))
    return lines


def _clean(raw: list[dict] | None) -> list[dict]:
    messages = []
    for m in raw or []:
        body = (m.get("body") or "").strip()
        if not body:
            continue
        speaker = m.get("speaker") or FIRST
        if speaker == "Maya":
            speaker = FIRST
        if speaker == "Arjun":
            speaker = SECOND
        kind = m.get("kind") or "text"
        if speaker not in LEADS and kind != "scene_marker":
            continue
        messages.append(
            {
                "speaker": None if kind == "scene_marker" else speaker,
                "body": body,
                "kind": kind,
            }
        )
    return messages[:8]


def _dialogue_user(chapter: dict, recent: list[dict], already: int, beat: dict, subtext: list, repair: str) -> str:
    blob = (
        f"Story bible: {BIBLE}\n"
        f"Chapter {chapter['n']} — {chapter['title']}\n"
        f"Objective: {chapter['objective']}\n"
        f"Emotional objective: {chapter['emotional_objective']}\n"
        f"Closing line to earn (do not paste it as dialogue): {chapter['closing']}\n"
        f"Scene director beat (obey this; do not write the beat as narration): {beat}\n"
        f"Subtext (what they mean, not what they write): {subtext}\n"
        f"First person (Deb writes the note in the input box): {FIRST}\n"
        f"Second person (Visha's note types in her bubble): {SECOND}\n"
        f"Recent notes: {recent[-16:]}\n"
        f"Messages already in this chapter: {already}\n"
        "Year 1850. Calcutta. Secret paper notes only — not a phone chat. "
        "Forbidden: phone, chat, typing, SMS, TV, traffic, car, Southern Avenue, "
        "Jadavpur, Rashbehari, internet, WhatsApp, modern slang. "
        "Allowed: courtyard, ghat, monsoon, pishi, proposal, reputation, ink, paper, lamp. "
        "Each note 1–2 short sentences. Dates belong in scene_marker only. "
        "Write the NEXT 4 to 7 notes only. Alternate speakers. "
        "Do not resolve the whole chapter unless already is high (>10). "
        "If the chapter should end now, set chapter_complete true and include a quiet cliffhanger."
    )
    if repair:
        blob += f"\nREPAIR and rewrite the notes: {repair}"
    return blob


async def _directed(
    chapter: dict,
    recent: list[dict],
    already: int,
    tension: int,
    provider: LLMProvider,
) -> dict[str, Any]:
    state = _state(chapter, already, tension)
    context = {
        "bible": BIBLE,
        "chapter_plan": {
            "objective": chapter["objective"],
            "emotional_objective": chapter["emotional_objective"],
            "escalation_target": chapter.get("escalation_target"),
            "title": chapter["title"],
            "n": chapter["n"],
        },
        "state": state,
        "recent": _recent_lines(recent),
        "threads": [t["name"] for t in THREADS],
    }
    beat = await scene_director.direct(provider, context)
    state = emotion_engine.apply_deltas(
        state, beat.get("emotional_shift") or {}, major_reveal=bool(beat.get("reveal"))
    )
    if "tension_delta" in beat:
        state["tension"] = emotion_engine.clamp(int(state.get("tension") or 0) + int(beat["tension_delta"]))

    subtext = await subtext_engine.for_beat(provider, beat, LEADS, state)

    repair = ""
    messages: list[dict] = []
    complete = False
    for _ in range(2):
        data = await provider.complete_json(
            prompts.DIALOGUE, _dialogue_user(chapter, recent, already, beat, subtext, repair)
        )
        messages = _clean(data.get("messages") if isinstance(data, dict) else None)
        complete = bool((data or {}).get("chapter_complete"))
        try:
            post_check([m["body"] for m in messages])
        except SafetyError as e:
            repair = str(e)
            continue
        verdict = await critic.review(provider, messages, BIBLE, _recent_lines(recent), LEADS)
        if verdict.get("pass"):
            break
        repair = verdict.get("repair_instruction") or "; ".join(verdict.get("issues") or [])
        if not repair:
            break

    complete = complete or bool(beat.get("cliffhanger")) or already + len(messages) >= 14
    return {
        "messages": messages,
        "chapter_complete": complete,
        "closing": chapter["closing"],
        "llm": True,
        "tension": int(state.get("tension") or 0),
    }


async def next_batch(
    chapter_index: int,
    recent: list[dict],
    already: int,
    tension: int = 0,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    chapter = CHAPTERS[chapter_index]
    if provider is None and not settings.api_key:
        return _canned(chapter, already)
    return await _directed(chapter, recent, already, tension, provider or get_provider())
