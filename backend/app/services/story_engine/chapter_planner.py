from __future__ import annotations

from app.llm import LLMProvider
from app.llm import prompts

DEFAULT_ARC = [
    ("প্রথম কথা", "First meaningful encounter", "curiosity", 22, "কেউ পুরোপুরি বলেনি কেন লিখল।"),
    ("জানার ইচ্ছে", "Curiosity", "curiosity", 34, "বৃষ্টি থামলেও কথা থামেনি।"),
    ("কাছাকাছি", "Emotional connection", "involvement", 48, "সে শুনেছিল। সেটাই যথেষ্ট ছিল।"),
    ("বাড়ির ছায়া", "Social obstacle appears", "conflict", 58, "নামটা সে মুখে আনেনি। তবু ঘর ভারী হয়েছিল।"),
    ("নিঃশব্দ ঘনিষ্ঠতা", "Growing intimacy", "intimacy", 66, "দেখা হয়নি। অপেক্ষাটা থেকে গেছে।"),
    ("লুকোনো টান", "Hidden conflict revealed", "conflict", 74, "সত্যিটা অন্য মুখে এসে পৌঁছাল।"),
    ("দূরত্ব", "Misunderstanding / separation", "separation", 70, "ডিলিট করা মেসেজটাই সব বলেছিল।"),
    ("ফিরে আসা", "Reconnection", "reconnection", 78, "আবার বৃষ্টি। আবার একই দুটো নাম।"),
    ("পছন্দের মুহূর্ত", "Major choice", "climax", 88, "কালকের বৈঠক। আজকের একটি প্রশ্ন।"),
    ("যা বলা হয়নি", "Climax and quiet consequence", "climax", 92, "কথাটা সে বলেনি। কিন্তু দুজনেই বুঝেছিল।"),
]


async def plan_chapters(provider: LLMProvider, bible: dict, n: int = 10) -> list[dict]:
    user = f"Story bible: {bible}\nDesired chapters: {n}\nGenre: romance\nTarget arc: slow-burn family-pressure romance."
    data = await provider.complete_json(prompts.CHAPTER_PLANNER, user)
    chapters = (data or {}).get("chapters") or []
    if len(chapters) >= n:
        return chapters[:n]
    return fallback_chapters(n)


def fallback_chapters(n: int = 10) -> list[dict]:
    out = []
    for i, row in enumerate(DEFAULT_ARC[:n], start=1):
        title, objective, emotion, tension, closing = row
        out.append(
            {
                "chapter_number": i,
                "title": title,
                "objective": objective,
                "emotional_objective": emotion,
                "conflict": "unspoken desire vs family expectation",
                "reveal": "a little more than last time, never everything",
                "key_scenes": ["late-night chat"],
                "escalation_target": tension,
                "cliffhanger": closing,
                "closing_line": closing,
            }
        )
    return out
