import json
import re
from typing import Any, Protocol

import httpx

from app.config import settings


class LLMProvider(Protocol):
    async def complete_json(self, system: str, user: str, cheap: bool = False) -> dict[str, Any]: ...


class OpenAICompatProvider:
    async def complete_json(self, system: str, user: str, cheap: bool = False) -> dict[str, Any]:
        payload = {
            "model": settings.model,
            "temperature": 0.8,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system + "\nReturn valid JSON only."},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {settings.api_key}"}
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(f"{settings.llm_base_url}/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
        return json.loads(text)


class MockProvider:
    """Deterministic JSON for tests and offline demo generation."""

    def __init__(self, canned: dict[str, Any] | None = None):
        self.canned = canned or {}

    async def complete_json(self, system: str, user: str, cheap: bool = False) -> dict[str, Any]:
        if "story director" in system.lower() or "scene director" in system.lower():
            return self.canned.get(
                "director",
                {
                    "scene_goal": "A quiet late-night exchange that reveals one withheld fact.",
                    "next_event": "One character almost says what they mean, then retreats.",
                    "slugline": "দৃশ্য · উঠোন · সন্ধ্যা",
                    "blocking": "Visha behind the household screen; Deb in the courtyard.",
                    "action": "Rain hits the tiles. A folded note is passed.",
                    "emotional_shift": {"relationship_tension": 2},
                    "reveal": False,
                    "cliffhanger": False,
                    "tension_delta": 4,
                },
            )
        if "subtext engine" in system.lower() or "hidden intent" in system.lower():
            return {
                "lines": [
                    {
                        "speaker": "Visha",
                        "literal_intent": "ask if he is awake",
                        "hidden_intent": "test whether he still wants to talk",
                        "fear": "he may have pulled away",
                        "desired_response": "he answers quickly",
                    }
                ]
            }
        if "fiction editor" in system.lower() or "critic" in system.lower():
            return {"pass": True, "issues": [], "repair_instruction": ""}
        if "story bible" in system.lower() or "canonical story bible" in system.lower():
            return self.canned.get("bible") or {
                "premise": "Deb and Visha under family pressure.",
                "setting": "Calcutta",
                "characters": [
                    {"name": "Deb", "age": 26, "backstory": "Clerk."},
                    {"name": "Visha", "age": 24, "backstory": "Reads in secret."},
                ],
            }
        if "chapter planner" in system.lower() or "10-chapter outline" in system.lower():
            return self.canned.get("planner", {"chapters": []})
        if "dialogue" in system.lower() or "write original bengali for fictional" in system.lower():
            return {
                "messages": [
                    {"speaker": "Deb", "body": "প্রদীপ জ্বলে আছে?", "kind": "text"},
                    {"speaker": "Visha", "body": "জ্বলে। তুমিও লিখছো?", "kind": "text"},
                    {"speaker": "Deb", "body": "কথাটা পরে লিখব ভেবেছিলাম। এখন মনে হচ্ছে পরে লিখলে আর অর্থ থাকবে না।", "kind": "text"},
                ],
                "chapter_complete": False,
            }
        return {}


def get_provider() -> LLMProvider:
    if settings.api_key:
        return OpenAICompatProvider()
    return MockProvider()


def extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("No JSON in model output")
    return json.loads(match.group(0))
