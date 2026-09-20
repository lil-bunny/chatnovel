from __future__ import annotations

from typing import Any

from app.config import settings
from app.llm import LLMProvider, get_provider
from app.llm import prompts
from app.plot import era_rules as default_era_rules
from app.seed_story import BIBLE, CHAPTERS, THREADS
from app.services.story_engine import critic, emotion_engine, scene_director, subtext_engine
from app.services.story_engine.safety import SafetyError, post_check

FIRST = "Deb"
SECOND = "Visha"
LEADS = [FIRST, SECOND]
SKIP_KINDS = ("scene_marker", "action")


def _canned(chapter: dict, already: int) -> dict[str, Any]:
    raw = chapter.get("messages") or []
    raw = raw[already : already + 8]
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
        "chapter_complete": already + len(msgs) >= len(chapter.get("messages") or []),
        "closing": chapter.get("closing") or "",
        "llm": False,
        "tension": int(chapter.get("escalation_target") or 0),
    }


def _state(chapter: dict, already: int, tension: int, setting: str) -> dict:
    t = tension or min(100, 18 + already * 3)
    return {
        "tension": t,
        "setting": setting,
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
        if m.get("kind") in SKIP_KINDS:
            continue
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
        if kind in SKIP_KINDS:
            messages.append({"speaker": None, "body": body, "kind": kind})
            continue
        if speaker not in LEADS:
            continue
        messages.append({"speaker": speaker, "body": body, "kind": kind})
    return messages[:8]


def _action_card(beat: dict) -> dict | None:
    slug = (beat.get("slugline") or "").strip()
    blocking = (beat.get("blocking") or "").strip()
    action = (beat.get("action") or "").strip()
    extra = " — ".join(x for x in (blocking, action) if x)
    body = slug if not extra else f"{slug}\n{extra}" if slug else extra
    if not body:
        return None
    return {"speaker": None, "kind": "action", "body": body, "slugline": slug, "blocking": blocking, "action": action}


def _dialogue_user(bible, chapter, recent, already, beat, subtext, rules, repair: str) -> str:
    blob = (
        f"Story bible: {bible}\n"
        f"Chapter {chapter.get('n')} — {chapter.get('title')}\n"
        f"Objective: {chapter.get('objective')}\n"
        f"Emotional objective: {chapter.get('emotional_objective')}\n"
        f"Closing line to earn (do not paste it as dialogue): {chapter.get('closing')}\n"
        f"Action beat (place only; do not narrate as a spoken line): {beat}\n"
        f"Subtext: {subtext}\n"
        f"era_rules: {rules}\n"
        f"Channel: {rules.get('channel')}\n"
        f"Forbidden: {rules.get('forbidden')}\n"
        f"Allowed: {rules.get('allowed')}\n"
        f"Delivery: {rules.get('delivery')}\n"
        f"First person (Deb, composer): {FIRST}\n"
        f"Second person (Visha, left bubble): {SECOND}\n"
        f"Recent: {recent[-16:]}\n"
        f"Messages already in this chapter: {already}\n"
        "Write the NEXT 4 to 7 lines only. Alternate speakers. "
        "Do not resolve the whole chapter unless already is high (>10). "
        "If the chapter should end now, set chapter_complete true and include a quiet cliffhanger."
    )
    if repair:
        blob += f"\nREPAIR and rewrite: {repair}"
    return blob


async def _directed(
    chapter: dict,
    recent: list[dict],
    already: int,
    tension: int,
    provider: LLMProvider,
    bible: dict,
    rules: dict,
) -> dict[str, Any]:
    state = _state(chapter, already, tension, rules.get("setting") or "Calcutta")
    context = {
        "bible": bible,
        "chapter_plan": {
            "objective": chapter.get("objective"),
            "emotional_objective": chapter.get("emotional_objective"),
            "escalation_target": chapter.get("escalation_target"),
            "title": chapter.get("title"),
            "n": chapter.get("n"),
            "key_scenes": chapter.get("key_scenes") or [],
            "reveal": chapter.get("conflict"),
        },
        "state": state,
        "recent": _recent_lines(recent),
        "threads": [t["name"] for t in THREADS],
        "era_rules": rules,
    }
    user_extra = (
        f"era_rules: {rules}\n"
        f"Key scenes (prefer these locations): {chapter.get('key_scenes')}\n"
        "Place Deb and Visha. Do not write their lines."
    )
    beat = await scene_director.direct(provider, {**context, "recent": context["recent"] + [user_extra]})
    state = emotion_engine.apply_deltas(
        state, beat.get("emotional_shift") or {}, major_reveal=bool(beat.get("reveal"))
    )
    if "tension_delta" in beat:
        state["tension"] = emotion_engine.clamp(int(state.get("tension") or 0) + int(beat["tension_delta"]))

    subtext = await subtext_engine.for_beat(provider, beat, LEADS, {**state, "era_rules": rules})

    repair = ""
    messages: list[dict] = []
    complete = False
    for _ in range(2):
        data = await provider.complete_json(
            prompts.DIALOGUE, _dialogue_user(bible, chapter, recent, already, beat, subtext, rules, repair)
        )
        messages = _clean(data.get("messages") if isinstance(data, dict) else None)
        complete = bool((data or {}).get("chapter_complete"))
        try:
            post_check([m["body"] for m in messages])
        except SafetyError as e:
            repair = str(e)
            continue
        verdict = await critic.review(
            provider,
            messages,
            bible,
            _recent_lines(recent) + [f"era_rules: {rules}"],
            LEADS,
        )
        if verdict.get("pass"):
            break
        repair = verdict.get("repair_instruction") or "; ".join(verdict.get("issues") or [])
        if not repair:
            break

    card = _action_card(beat)
    if card and already == 0:
        messages = [card, *[m for m in messages if m.get("kind") != "action"]]
    elif card:
        last = (recent[-1] if recent else {}) or {}
        if last.get("kind") != "action":
            messages = [card, *[m for m in messages if m.get("kind") != "action"]]

    complete = complete or bool(beat.get("cliffhanger")) or already + len(messages) >= 14
    return {
        "messages": messages,
        "chapter_complete": complete,
        "closing": chapter.get("closing") or "",
        "llm": True,
        "tension": int(state.get("tension") or 0),
    }


async def next_batch(
    chapter_index: int,
    recent: list[dict],
    already: int,
    tension: int = 0,
    pack: dict | None = None,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    pack = pack or {}
    bible = pack.get("bible") or BIBLE
    chapters = pack.get("chapters") or CHAPTERS
    rules = pack.get("era_rules") or default_era_rules("calcutta_1850")
    idx = max(0, min(chapter_index, len(chapters) - 1))
    chapter = chapters[idx]
    if provider is None and not settings.api_key and chapter.get("messages"):
        return _canned(chapter, already)
    return await _directed(
        chapter, recent, already, tension, provider or get_provider(), bible, rules
    )
