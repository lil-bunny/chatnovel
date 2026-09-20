MIN_AGE = 18
UNDERAGE = ("underage", "child sex", "নিম্নবয়সী")
GRAPHIC = ("porn", "explicit sex")


class SafetyError(ValueError):
    pass


def assert_adult_cast(characters: list) -> None:
    for c in characters:
        if c.age < MIN_AGE:
            raise SafetyError(f"{c.name} is not confirmed 18+")


def classify_intensity(text: str) -> str:
    lowered = text.lower()
    if any(w in lowered for w in UNDERAGE):
        return "blocked"
    if any(w in lowered for w in GRAPHIC):
        return "graphic"
    return "tasteful"


def pre_check(characters: list, brief: str = "") -> None:
    assert_adult_cast(characters)
    if classify_intensity(brief) == "blocked":
        raise SafetyError("Requested intensity is not allowed")


def post_check(bodies: list[str], heat: str = "restrained") -> None:
    blob = "\n".join(bodies)
    rank = classify_intensity(blob)
    if rank == "blocked":
        raise SafetyError("Generated text failed safety")
    if heat != "erotic" and rank == "graphic":
        raise SafetyError("Generated text failed safety")
    if any(x in blob for x in ("১৬ বছর", "১৭ বছর", "16 years", "17 years", "schoolgirl")):
        raise SafetyError("Age-uncertain or underage content")
