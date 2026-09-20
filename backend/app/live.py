"""Two-phone live RP. In-memory rooms — no database."""

from __future__ import annotations

import secrets
import threading
from typing import Any

from app.llm import LLMProvider, get_provider
from app.llm import prompts

LEADS = ("Deb", "Visha")
# ponytail: process-global dict; one Render box; restart wipes rooms. Upgrade: Redis.
_lock = threading.Lock()
ROOMS: dict[str, dict[str, Any]] = {}
_ABC = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _code() -> str:
    return "".join(secrets.choice(_ABC) for _ in range(4))


def create() -> dict:
    with _lock:
        for _ in range(12):
            rid = _code()
            if rid not in ROOMS:
                ROOMS[rid] = {"id": rid, "seats": {"Deb": False, "Visha": False}, "messages": [], "n": 0, "hints": []}
                return snapshot(rid)
        raise RuntimeError("could not mint room")


def snapshot(rid: str, after: int = 0) -> dict:
    room = ROOMS.get(rid)
    if not room:
        raise KeyError("no room")
    msgs = [m for m in room["messages"] if m["n"] > after]
    return {
        "id": rid,
        "seats": dict(room["seats"]),
        "messages": msgs,
        "after": room["n"],
        "hints": list(room.get("hints") or []),
    }


def join(rid: str, role: str) -> dict:
    if role not in LEADS:
        raise ValueError("role")
    with _lock:
        room = ROOMS.get(rid)
        if not room:
            raise KeyError("no room")
        if room["seats"][role]:
            raise ValueError("taken")
        room["seats"][role] = True
        return snapshot(rid)


def _push(room: dict, kind: str, speaker: str | None, body: str, raw: str = "") -> dict:
    room["n"] += 1
    msg = {"n": room["n"], "kind": kind, "speaker": speaker, "body": body, "raw": raw}
    room["messages"].append(msg)
    return msg


async def say(rid: str, role: str, text: str, provider: LLMProvider | None = None) -> dict:
    text = (text or "").strip()
    if role not in LEADS:
        raise ValueError("role")
    if not text:
        raise ValueError("empty")
    with _lock:
        room = ROOMS.get(rid)
        if not room:
            raise KeyError("no room")
        recent = room["messages"][-12:]
    p = provider or get_provider()
    action, body, hints = await _expand(p, role, text, recent)
    with _lock:
        room = ROOMS.get(rid)
        if not room:
            raise KeyError("no room")
        _push(room, "action", None, action, text)
        _push(room, "text", role, body, text)
        room["hints"] = hints
        return snapshot(rid, after=max(0, room["n"] - 2))


async def _expand(provider: LLMProvider, role: str, text: str, recent: list[dict]) -> tuple[str, str, list[str]]:
    other = "Visha" if role == "Deb" else "Deb"
    scene = []
    for m in recent[-8:]:
        who = m.get("speaker") or "action"
        scene.append(f"{who}: {m.get('body') or ''}")
    user = (
        f"Speaker: {role} (age {26 if role == 'Deb' else 24}). Other is {other}.\n"
        f"They typed (DO THIS ACT): {text}\n"
        f"SCENE SO FAR:\n" + ("\n".join(scene) if scene else "(nothing yet — they are together in a private room)") + "\n"
        "Do the act they asked for on the current bodies. Name body parts. English. "
        "Do not write the other person. Include 3 next suggestions."
    )
    data = await provider.complete_json(prompts.LIVE_ELABORATE, user)
    action = str((data or {}).get("action") or "").strip()
    body = str((data or {}).get("body") or "").strip()
    raw_next = (data or {}).get("next") or []
    hints = [str(x).strip() for x in raw_next if str(x).strip()][:4]
    if not action:
        action = f"{role} does what they said: {text}"
    if not body:
        body = text
    if not hints:
        hints = ["kiss their neck", "hand on their chest", "pull them closer"]
    return action, body, hints
