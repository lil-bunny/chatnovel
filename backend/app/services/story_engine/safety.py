MIN_AGE = 18
GRAPHIC = ("porn", "explicit sex", "underage", "child sex", "নিম্নবয়সী")


class SafetyError(ValueError):
    pass


def assert_adult_cast(characters: list) -> None:
    for c in characters:
        if c.age < MIN_AGE:
            raise SafetyError(f"{c.name} is not confirmed 18+")


def classify_intensity(text: str) -> str:
    lowered = text.lower()
    if any(w in lowered for w in GRAPHIC):
        return "blocked"
    return "tasteful"


def pre_check(characters: list, brief: str = "") -> None:
    assert_adult_cast(characters)
    if classify_intensity(brief) == "blocked":
        raise SafetyError("Requested intensity is not allowed")


def post_check(bodies: list[str]) -> None:
    blob = "\n".join(bodies)
    if classify_intensity(blob) == "blocked":
        raise SafetyError("Generated text failed safety")
    if any(x in blob for x in ("১৬ বছর", "১৭ বছর", "16 years", "17 years", "schoolgirl")):
        raise SafetyError("Age-uncertain or underage content")
