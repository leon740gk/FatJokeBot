"""Quiz questions live in knowledge_base/fat_joke/quiz/<code>.json, one file per discipline.

{
  "code": "mlbb2",               # must match the file name, goes into callback_data
  "title": "MLBB 2",
  "shuffle_options": true,       # optional, shuffle options every time the question is asked
  "questions": [
    {"number": 1, "text": "...", "options": ["a", "b", "c", "d"], "correct": [1], "explanation": "optional"}
  ]
}
"""

import json
from dataclasses import dataclass
from pathlib import Path

QUIZ_DIR = Path(__file__).resolve().parents[3] / "knowledge_base" / "fat_joke" / "quiz"
OPTIONS_COUNT = 4


@dataclass(frozen=True)
class Question:
    discipline: str
    number: int
    text: str
    options: tuple
    correct: frozenset  # indexes into options
    explanation: str | None = None

    def correct_options(self):
        return [option for index, option in enumerate(self.options) if index in self.correct]


@dataclass(frozen=True)
class Discipline:
    code: str
    title: str
    questions: dict
    shuffle_options: bool = False


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


def load_discipline(path):
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    code = raw.get("code")
    if code != path.stem:
        raise ValueError(f"{path.name}: code {code!r} must match the file name")
    questions = {}
    for raw_question in raw.get("questions", []):
        question = _load_question(code, raw_question, path)
        if question.number in questions:
            raise ValueError(f"{path.name}: question number {question.number} is used twice")
        questions[question.number] = question
    if not questions:
        raise ValueError(f"{path.name}: no questions")
    return Discipline(code, raw["title"], questions, bool(raw.get("shuffle_options")))


def load_disciplines(directory=QUIZ_DIR):
    return {discipline.code: discipline for discipline in map(load_discipline, sorted(Path(directory).glob("*.json")))}
