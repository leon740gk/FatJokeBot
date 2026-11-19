"""Quiz questions live in knowledge_base/<bot>/quiz/<code>.json, one file per discipline.

{
  "code": "mlbb2",               # must match the file name, goes into callback_data
  "title": "MLBB 2",
  "aliases": ["мобла", "моба"],  # optional, how people call the topic in "/quiz мобла"
  "shuffle_options": true,       # optional, shuffle options every time the question is asked
  "questions": [
    {"number": 1, "text": "...", "options": ["a", "b", "c", "d"], "correct": [1], "explanation": "optional"}
  ]
}

A picture topic has "memes" instead of "questions": the questions are made from what is known of each meme,
the wrong options are the same facts of other memes. Only memes with a photo (a Telegram file id of this bot,
see telegram_bots/upload_memes.py) are asked, a topic without any is not loaded at all.

{
  "code": "memes",
  "title": "Мемология",
  "asks": {"name": "Как называется этот мем?", "year": "...", "origin": "...", "author": "..."},
  "facts": {"year": "Год: {year}", "origin": "Откуда: {origin}", "author": "Автор: {author}"},
  "memes": [
    {"number": 1, "code": "doge", "name": "Доге", "year": 2013, "origin": "...", "author": "...", "photo": "file id"}
  ]
}
"year", "origin" and "author" are optional, a meme is asked only about what it has; "hide_name": true when the
picture itself says the name. A meme's question numbers are its number * 10 + 1 for the name, 2 for the year,
3 for the origin and 4 for the author, so they stay the same when memes are added.
"""

import json
import random
from dataclasses import dataclass
from pathlib import Path

OPTIONS_COUNT = 4
MEME_FACTS = ("name", "year", "origin", "author")
# the wrong years are this close to the right one
YEAR_SPREAD = 4


@dataclass(frozen=True)
class Question:
    discipline: str
    number: int
    text: str
    options: tuple
    correct: frozenset  # indexes into options
    explanation: str | None = None
    photo: str | None = None  # Telegram file id, the question is its caption

    def correct_options(self):
        return [option for index, option in enumerate(self.options) if index in self.correct]


@dataclass(frozen=True)
class Discipline:
    code: str
    title: str
    questions: dict
    shuffle_options: bool = False
    aliases: tuple = ()

    @property
    def has_photos(self):
        return any(question.photo for question in self.questions.values())


def _load_question(code, raw, path):
    where = f"{path.name}, question {raw.get('number')}"
    number, options, correct = raw.get("number"), raw.get("options"), raw.get("correct")
    if not isinstance(number, int) or number < 1:
        raise ValueError(f"{where}: number must be a positive integer")
    if not str(raw.get("text", "")).strip():
        raise ValueError(f"{where}: empty text")
    if not isinstance(options, list) or len(options) != OPTIONS_COUNT or not all(str(o).strip() for o in options):
        raise ValueError(f"{where}: needs exactly {OPTIONS_COUNT} non-empty options")
    if not correct or not all(isinstance(i, int) and 0 <= i < OPTIONS_COUNT for i in correct):
        raise ValueError(f"{where}: correct must list option indexes 0-{OPTIONS_COUNT - 1}")
    return Question(code, number, raw["text"].strip(), tuple(options), frozenset(correct), raw.get("explanation"))


def _wrong_options(right, others, rng):
    choices = sorted({other for other in others if other != right})
    if len(choices) < OPTIONS_COUNT - 1:
        return None
    return rng.sample(choices, OPTIONS_COUNT - 1)


def _wrong_years(year, rng):
    return rng.sample([other for other in range(year - YEAR_SPREAD, year + YEAR_SPREAD + 1) if other != year], 3)


def _meme_questions(code, raw, path):
    memes = raw.get("memes", [])
    numbers = [meme.get("number") for meme in memes]
    if not all(isinstance(number, int) and number > 0 for number in numbers) or len(set(numbers)) != len(numbers):
        raise ValueError(f"{path.name}: every meme needs its own positive number")
    asks, facts = raw["asks"], raw["facts"]
    questions = {}
    for meme in memes:
        if not meme.get("photo"):
            continue
        known = [fact for fact in MEME_FACTS if meme.get(fact) and not (fact == "name" and meme.get("hide_name"))]
        about = [f"«{meme['name']}»"] + [facts[fact].format(**meme) for fact in MEME_FACTS[1:] if meme.get(fact)]
        for index, fact in enumerate(MEME_FACTS, start=1):
            if fact not in known:
                continue
            number = meme["number"] * 10 + index
            # the same wrong options every time the bot starts
            rng = random.Random(number)
            right = str(meme[fact])
            if fact == "year":
                wrong = [str(year) for year in _wrong_years(meme[fact], rng)]
            else:
                wrong = _wrong_options(right, [str(other[fact]) for other in memes if other.get(fact)], rng)
            if not wrong:
                continue
            options = tuple([right, *wrong])
            questions[number] = Question(
                code, number, asks[fact], options, frozenset([0]), "\n".join(about), meme["photo"]
            )
    return questions


def load_discipline(path):
    """The Discipline of a quiz file; None for a picture topic without any photos yet."""
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    code = raw.get("code")
    if code != path.stem:
        raise ValueError(f"{path.name}: code {code!r} must match the file name")
    if "memes" in raw:
        questions = _meme_questions(code, raw, path)
        if not questions:
            return None
    else:
        questions = {}
        for raw_question in raw.get("questions", []):
            question = _load_question(code, raw_question, path)
            if question.number in questions:
                raise ValueError(f"{path.name}: question number {question.number} is used twice")
            questions[question.number] = question
    if not questions:
        raise ValueError(f"{path.name}: no questions")
    aliases = raw.get("aliases", [])
    if not isinstance(aliases, list) or not all(isinstance(alias, str) and alias.strip() for alias in aliases):
        raise ValueError(f"{path.name}: aliases must be a list of non-empty strings")
    aliases = tuple(alias.strip().lower() for alias in aliases)
    # the right option of a meme question always comes first, the buttons must be shuffled
    shuffle = bool(raw.get("shuffle_options")) or "memes" in raw
    return Discipline(code, raw["title"], questions, shuffle, aliases)


def load_disciplines(directory):
    disciplines = map(load_discipline, sorted(Path(directory).glob("*.json")))
    return {discipline.code: discipline for discipline in disciplines if discipline}
