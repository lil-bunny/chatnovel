"""Preset plot packs. Deb/Visha locked. No database."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.llm import LLMProvider, get_provider
from app.llm import prompts
from app.seed_story import BIBLE, CHAPTERS

TROPES = [
    {"id": "slow_burn", "label": "যা বলা হয়নি"},
    {"id": "enemies_to_lovers", "label": "শত্রু থেকে প্রেম"},
    {"id": "arranged", "label": "ঘরের বিয়ে"},
    {"id": "second_chance", "label": "দ্বিতীয় সুযোগ"},
]

ERAS = [
    {"id": "calcutta_1850", "label": "গোপন চিঠি, ১৮৫০"},
    {"id": "modern", "label": "আজকের কলকাতা"},
    {"id": "sarat_era", "label": "পুরনো সামাজিক রোমান্স"},
]

HEATS = [
    {"id": "restrained", "label": "সংযত"},
    {"id": "erotic", "label": "কামুক"},
]

HEAT_SPEC = {
    "restrained": "Restrained romance. Longing and implication. No graphic sex.",
    "erotic": (
        "Full erotica between Deb (26) and Visha (24). Must write: hands on cloth, "
        "opening dress/sari/blouse/shirt (era-true), skin, mouths, exploring the body, intercourse. "
        "Action beat is 4–8 Bengali sentences. Do not fade to black. Do not imply and cut away."
    ),
}

TROPE_BEATS = {
    "slow_burn": "Unspoken attachment. Neither confesses. Family pressure gathers. Quiet choice at the end.",
    "enemies_to_lovers": "They begin in friction and pride. Insults hide interest. A shared crisis forces honesty. Attraction arrives late and costs them.",
    "arranged": "A suitable match is being arranged around Visha. Deb is the wrong standing or the wrong time. Duty and wanting collide.",
    "second_chance": "They knew each other before and parted badly. A return to the same city. Old wound, new chance, same families.",
}

ERAS_SPEC = {
    "calcutta_1850": {
        "channel": "notes",
        "setting": "Company-era Calcutta, 1850. Courtyards, monsoon, lamp-light.",
        "blurb": "১৮৫০, কলকাতা। Deb আর Visha-এর গোপন চিঠি।",
        "forbidden": "phone, chat, typing, SMS, TV, traffic, car, Southern Avenue, Jadavpur, Rashbehari, internet, WhatsApp, modern slang",
        "allowed": "courtyard, ghat, monsoon, pishi, proposal, reputation, ink, paper, lamp, household screen",
        "delivery": "folded paper notes, not a phone",
        "action_locations": "courtyards, ghats, rented rooms, household screens, lamps",
        "literary": "restrained 1850 Bengal; original; do not copy any author",
    },
    "modern": {
        "channel": "chat",
        "setting": "Present-day Kolkata. Apartments, buses, tea stalls, late phones.",
        "blurb": "আজকের কলকাতা। Deb আর Visha-এর চ্যাট।",
        "forbidden": "do not use period-only props as if they replace phones",
        "allowed": "phone, chat, bus, cafe, Southern Avenue, flat, office, family pressure",
        "delivery": "short phone messages in the chat UI",
        "action_locations": "cafes, buses, rooftops, flats, office corridors, tea stalls",
        "literary": "accessible contemporary Bengali; not 2020s meme slang wall; original",
    },
    "sarat_era": {
        "channel": "notes",
        "setting": "Early 1900s Bengal. Village and town, household honour, letters.",
        "blurb": "পুরনো বাংলা। Deb আর Visha-এর চিঠি। নতুন গল্প, কারও নকল নয়।",
        "forbidden": "phone, car, TV, internet, WhatsApp, copy or mimic Sarat Chandra or any named author",
        "allowed": "courtyard, pond, train, letter, pishi, village path, town lodging, oil lamp, reputation, sacrifice",
        "delivery": "letters and stolen notes",
        "action_locations": "village courtyards, ponds, station benches, town lodgings, inner rooms",
        "literary": "duty vs desire, honour, village/city pressure, sacrifice; ORIGINAL prose only; do not imitate Sarat Chandra",
    },
}


def presets() -> dict:
    return {
        "tropes": TROPES,
        "eras": ERAS,
        "heats": HEATS,
        "defaults": {"trope": "slow_burn", "era": "calcutta_1850", "heat": "restrained"},
    }


def era_rules(era: str, heat: str = "restrained") -> dict:
    spec = ERAS_SPEC.get(era) or ERAS_SPEC["calcutta_1850"]
    h = heat if heat in HEAT_SPEC else "restrained"
    return {
        "era": era if era in ERAS_SPEC else "calcutta_1850",
        "heat": h,
        "heat_direction": HEAT_SPEC[h],
        **spec,
    }


def _lock_leads(bible: dict, spec: dict) -> dict:
    bible = dict(bible or {})
    leads = [
        {
            "name": "Deb",
            "age": 26,
            "pronouns": "he/him",
            "role": "lead",
            "personality": {"restraint": "high", "pride": "defensive"},
            "speech_style": {"length": "medium", "directness": "delayed"},
            "goals": ["not to look foolish"],
            "fears": ["arriving too late"],
            "secrets": ["he has already chosen her in private"],
            "backstory": "Modest standing. Writes more than he speaks.",
        },
        {
            "name": "Visha",
            "age": 24,
            "pronouns": "she/her",
            "role": "lead",
            "personality": {"restraint": "high", "pride": "quiet"},
            "speech_style": {"length": "short", "questions": "oblique"},
            "goals": ["to be chosen without having to ask"],
            "fears": ["becoming a family disappointment"],
            "secrets": ["she has imagined a life the house may not allow"],
            "backstory": "Lives with family. Reads more than she is allowed to show.",
        },
    ]
    incoming = {str(c.get("name") or "").lower(): c for c in bible.get("characters") or [] if isinstance(c, dict)}
    out = []
    for base in leads:
        extra = incoming.get(base["name"].lower()) or {}
        merged = {**base, **{k: extra[k] for k in extra if k not in ("name", "age")}}
        merged["name"] = base["name"]
        merged["age"] = base["age"]
        if int(merged.get("age") or 0) < 18:
            merged["age"] = base["age"]
        out.append(merged)
    bible["characters"] = out
    bible["setting"] = bible.get("setting") or spec["setting"]
    bible["literary_direction"] = spec["literary"]
    return bible


def _norm_chapter(raw: dict, i: int) -> dict:
    n = int(raw.get("n") or raw.get("chapter_number") or i)
    closing = (raw.get("closing") or raw.get("closing_line") or raw.get("cliffhanger") or "").strip()
    scenes = raw.get("key_scenes") or []
    if isinstance(scenes, str):
        scenes = [scenes]
    return {
        "n": n,
        "title": raw.get("title") or f"অধ্যায় {n}",
        "closing": closing,
        "objective": raw.get("objective") or "",
        "emotional_objective": raw.get("emotional_objective") or "",
        "conflict": raw.get("conflict") or "",
        "escalation_target": int(raw.get("escalation_target") or min(92, 18 + n * 8)),
        "key_scenes": [str(s) for s in scenes][:3],
        "messages": raw.get("messages") or [],
    }


def _from_seed(spec: dict, trope: str, era: str, heat: str = "restrained") -> dict[str, Any]:
    chapters = [_norm_chapter(c, c["n"]) for c in CHAPTERS]
    return {
        "title": "যা বলা হয়নি",
        "blurb": spec["blurb"],
        "first_person": "Deb",
        "second_person": "Visha",
        "bible": _lock_leads(dict(BIBLE), spec),
        "chapters": chapters,
        "channel": spec["channel"],
        "era_rules": era_rules(era, heat),
        "trope": trope,
        "era": era,
        "heat": heat,
        "llm": False,
    }


def _pack(bible: dict, chapters: list[dict], spec: dict, trope: str, era: str, heat: str, llm: bool) -> dict[str, Any]:
    return {
        "title": "যা বলা হয়নি",
        "blurb": spec["blurb"],
        "first_person": "Deb",
        "second_person": "Visha",
        "bible": bible,
        "chapters": chapters,
        "channel": spec["channel"],
        "era_rules": era_rules(era, heat),
        "trope": trope,
        "era": era,
        "heat": heat,
        "llm": llm,
        "characters": bible.get("characters") or [],
    }


async def compose(trope: str, era: str, heat: str = "restrained", provider: LLMProvider | None = None) -> dict[str, Any]:
    if trope not in TROPE_BEATS or era not in ERAS_SPEC or heat not in HEAT_SPEC:
        raise ValueError("unknown preset")
    spec = ERAS_SPEC[era]
    if provider is None and not settings.api_key:
        return _from_seed(spec, trope, era, heat)
    p = provider or get_provider()
    user_bible = (
        f"Leads MUST be Deb (26, he/him) and Visha (24, she/her). Adults 18+ only.\n"
        f"Trope: {trope} — {TROPE_BEATS[trope]}\n"
        f"Setting: {spec['setting']}\nChannel: {spec['channel']}\n"
        f"Heat: {heat} — {HEAT_SPEC[heat]}\n"
        f"Literary direction: {spec['literary']}\n"
        f"Do not copy or closely mimic any existing author, including Sarat Chandra.\n"
        "Invent original backstory, secrets, social pressure. Return the story bible JSON."
    )
    bible = _lock_leads(await p.complete_json(prompts.STORY_BIBLE, user_bible) or {}, spec)
    user_plan = (
        f"Story bible: {bible}\nHeat: {heat} — {HEAT_SPEC[heat]}\n"
        "Write exactly 10 chapters for Deb and Visha.\n"
        "Arc: encounter, pressure, almost-meeting, rupture, reconnection, "
        "chapter 9 climax/choice, chapter 10 quiet ending.\n"
        "Each chapter needs key_scenes (1-2 locations), Bengali closing_line, escalation_target 20-95.\n"
        "If heat is erotic, at least two chapters need private-room key_scenes "
        "(inner room, bedroom, locked door) where they can undress.\n"
        "Allow setbacks. Original titles. Do not write dialogue."
    )
    planned = (await p.complete_json(prompts.CHAPTER_PLANNER, user_plan) or {}).get("chapters") or []
    chapters = [_norm_chapter(c, i + 1) for i, c in enumerate(planned[:10])]
    if len(chapters) < 10:
        seed = _from_seed(spec, trope, era, heat)["chapters"]
        chapters.extend(seed[len(chapters) :])
        chapters = chapters[:10]
    for i, ch in enumerate(chapters, start=1):
        ch["n"] = i
        ch["messages"] = []
    return _pack(bible, chapters, spec, trope, era, heat, llm=True)
