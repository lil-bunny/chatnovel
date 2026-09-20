from __future__ import annotations

EMOTION_KEYS = [
    "affection",
    "trust",
    "longing",
    "fear",
    "jealousy",
    "pride",
    "vulnerability",
    "frustration",
    "hope",
    "resentment",
]

REL_KEYS = [
    "attraction",
    "trust",
    "emotional_intimacy",
    "conflict",
    "uncertainty",
    "commitment",
    "social_pressure",
]


def clamp(n: int) -> int:
    return max(0, min(100, n))


def apply_deltas(state: dict, shift: dict, major_reveal: bool = False) -> dict:
    """Emotion values change only with scene evidence. Huge jumps need a reveal."""
    cap = 25 if major_reveal else 8
    chars = state.setdefault("characters", {})
    rel = state.setdefault("relationship", {})
    for key, raw in (shift or {}).items():
        try:
            delta = int(raw)
        except (TypeError, ValueError):
            continue
        delta = max(-cap, min(cap, delta))
        if key in REL_KEYS or key == "relationship_tension":
            rk = "conflict" if key == "relationship_tension" else key
            rel[rk] = clamp(int(rel.get(rk) or 0) + delta)
            continue
        if "_" in key:
            name, dim = key.split("_", 1)
            person = chars.setdefault(name.lower(), {})
            if dim in EMOTION_KEYS:
                person[dim] = clamp(int(person.get(dim) or 0) + delta)
        elif key in EMOTION_KEYS:
            for person in chars.values():
                person[key] = clamp(int(person.get(key) or 0) + delta // 2)
    tension = int(state.get("tension") or 20)
    extra = int(shift.get("tension_delta") or 0)
    extra = max(-cap, min(cap, extra))
    state["tension"] = clamp(tension + extra)
    return state


def snapshot_for_character(state: dict, name: str) -> dict:
    return dict((state.get("characters") or {}).get(name.lower()) or {})
