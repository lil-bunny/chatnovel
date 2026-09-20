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
                ROOMS[rid] = {"id": rid, "seats": {"Deb": False, "Visha": False}, "messages": [], "n": 0}
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
    action, body = await _expand(p, role, text, recent)
    with _lock:
        room = ROOMS.get(rid)
        if not room:
            raise KeyError("no room")
        _push(room, "action", None, action, text)
        _push(room, "text", role, body, text)
        return snapshot(rid, after=max(0, room["n"] - 2))


async def _expand(provider: LLMProvider, role: str, text: str, recent: list[dict]) -> tuple[str, str]:
    other = "Visha" if role == "Deb" else "Deb"
    user = (
        f"Speaker: {role} (age {26 if role == 'Deb' else 24}). Other is {other}.\n"
        f"They typed: {text}\n"
        f"Recent: {recent[-8:]}\n"
        "Expand this one line into deep action + their chat. English. Do not write the other person."
    )
    data = await provider.complete_json(prompts.LIVE_ELABORATE, user)
    action = str((data or {}).get("action") or "").strip()
    body = str((data or {}).get("body") or "").strip()
    if not action:
        action = f"{role} does what they said: {text}"
    if not body:
        body = text
    return action, body
