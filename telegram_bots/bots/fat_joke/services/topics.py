"""Understands which quiz discipline people mean: "/quiz мобла", "/quiz по бухгалтерии", "/quiz geo"."""

import re

# words around the topic that don't name it
FILLER_WORDS = {
    "по",
    "про",
    "о",
    "об",
    "з",
    "із",
    "зі",
    "из",
    "хочу",
    "дай",
    "давай",
    "вопрос",
    "питання",
    "тема",
    "тему",
}
# "мобле" -> "мобла", "бухгалтерии" -> "бухгалтер": Russian and Ukrainian endings change, the stem stays
STEM_LENGTH = 4


def _names(discipline):
    return {discipline.code.lower(), discipline.title.lower(), *discipline.aliases}


def resolve_discipline(text, disciplines):
    """Returns the discipline code, or None when the text names no discipline or several of them."""
    phrase = " ".join(re.findall(r"[\w']+", (text or "").lower()))
    if not phrase:
        return None
    for code, discipline in disciplines.items():
        if phrase in _names(discipline):
            return code

    words = [word for word in phrase.split() if word not in FILLER_WORDS]
    exact = {code for code, discipline in disciplines.items() for word in words if word in _names(discipline)}
    if exact:
        return exact.pop() if len(exact) == 1 else None

    by_stem = {
        code
        for code, discipline in disciplines.items()
        for word in words
        for name in _names(discipline)
        if " " not in name
        and len(word) >= STEM_LENGTH
        and len(name) >= STEM_LENGTH
        and word[:STEM_LENGTH] == name[:STEM_LENGTH]
    }
    return by_stem.pop() if len(by_stem) == 1 else None
