import random
from dataclasses import dataclass, field
from enum import Enum

from telegram_bots.bots.fat_joke.db import quiz as quiz_db
from telegram_bots.bots.fat_joke.db import settings
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.services import iq
from telegram_bots.bots.fat_joke.services.quiz_bank import load_disciplines

DISCIPLINES = load_disciplines()
DEFAULT_DISCIPLINE = "mlbb2"
DISCIPLINE_SETTING = "quiz_discipline"
# longest option that still fits on a button: two buttons per row, or one per row
SHORT_OPTION = 14
BUTTON_OPTION = 30


class Outcome(Enum):
    CLOSED = "closed"  # old button, time is up, or someone has already answered this message
    CHEATER = "cheater"
    CORRECT = "correct"
    WRONG = "wrong"


@dataclass(frozen=True)
class AnswerResult:
    outcome: Outcome
    text: str = ""


@dataclass(frozen=True)
class ParsedAnswer:
    discipline: str
    number: int
    option_index: int


@dataclass(frozen=True)
class RenderedQuestion:
    text: str
    rows: list = field(default_factory=list)  # rows of (button label, callback_data)


@dataclass(frozen=True)
class PickResult:
    question: object
    season: int
    finished_season: int | None = None  # set when the previous season has just run out of questions
    winners: list = field(default_factory=list)


def current_discipline(db):
    code = settings.get(db, DISCIPLINE_SETTING, DEFAULT_DISCIPLINE)
    return code if code in DISCIPLINES else DEFAULT_DISCIPLINE


def set_discipline(db, code):
    settings.set_value(db, DISCIPLINE_SETTING, code)


def title(code):
    return DISCIPLINES[code].title


def get_question(discipline, number):
    if discipline not in DISCIPLINES:
        return None
    return DISCIPLINES[discipline].questions.get(number)


def pick_question(db, discipline, rng=random):
    """Picks a question nobody has been asked this season; starts a new season when they run out."""
    season = quiz_db.current_season(db, discipline)
    asked = quiz_db.get_asked_numbers(db, discipline, season)
    numbers = [number for number in DISCIPLINES[discipline].questions if number not in asked]
    if numbers:
        return PickResult(get_question(discipline, rng.choice(numbers)), season)

    winners = quiz_db.get_leaders(db, discipline, season)
    quiz_db.finish_season(db, discipline, season)
    new_season = quiz_db.current_season(db, discipline)
    question = get_question(discipline, rng.choice(list(DISCIPLINES[discipline].questions)))
    return PickResult(question, new_season, finished_season=season, winners=winners)


def option_callback_data(question, option_index):
    return f"q {question.discipline} {question.number} {option_index}"


def render_question(question, rng=random):
    order = list(range(len(question.options)))
    if DISCIPLINES[question.discipline].shuffle_options:
        rng.shuffle(order)
    header = f"{title(question.discipline)}.\n{question.text}"
    longest = max(len(option) for option in question.options)

    if longest <= BUTTON_OPTION:
        buttons = [(question.options[index], option_callback_data(question, index)) for index in order]
        per_row = 2 if longest <= SHORT_OPTION else 1
        return RenderedQuestion(header, [buttons[i : i + per_row] for i in range(0, len(buttons), per_row)])

    # long options don't fit on buttons: list them in the message and number the buttons
    lines = [f"{position}) {question.options[index]}" for position, index in enumerate(order, start=1)]
    buttons = [(str(position), option_callback_data(question, index)) for position, index in enumerate(order, start=1)]
    return RenderedQuestion(header + "\n\n" + "\n".join(lines), [buttons[0:2], buttons[2:4]])


def parse_callback(data):
    # "q <discipline> <question_number> <option_index>", see option_callback_data
    parts = (data or "").split(" ")
    if len(parts) != 4 or parts[0] != "q" or not parts[2].isdigit() or not parts[3].isdigit():
        return None
    parsed = ParsedAnswer(parts[1], int(parts[2]), int(parts[3]))
    question = get_question(parsed.discipline, parsed.number)
    if not question or parsed.option_index >= len(question.options):
        return None
    return parsed


def answer_details(question):
    correct = ", ".join(question.correct_options())
    details = f"Правильна відповідь: {correct}"
    if question.explanation:
        details += f"\n{question.explanation}"
    return details


def process_answer(db, user_id, chat_id, message_id, callback_data):
    parsed = parse_callback(callback_data)
    if not parsed:
        return AnswerResult(Outcome.CLOSED)
    season = quiz_db.claim_quiz_message(db, chat_id, message_id, parsed.discipline, parsed.number, user_id)
    if season is None:
        return AnswerResult(Outcome.CLOSED)

    # correctness comes from the question bank, not from the button, so it can't be forged
    question = get_question(parsed.discipline, parsed.number)
    is_correct = parsed.option_index in question.correct
    iq_old, user_name = users_db.get_iq_and_name(db, user_id)
    if not quiz_db.save_answer(db, user_id, parsed.discipline, season, parsed.number, is_correct):
        return AnswerResult(Outcome.CHEATER, iq.anti_cheat_message(user_name))

    iq_new, message = iq.change_message(iq_old, user_name, increase=is_correct)
    users_db.set_iq(db, user_id, iq_new)
    text = f"{question.text}\n{message.strip()}\n\n{answer_details(question)}"
    return AnswerResult(Outcome.CORRECT if is_correct else Outcome.WRONG, text)


def expired_text(question):
    header = f"{title(question.discipline)}.\n{question.text}"
    return f"{header}\n\n⏰ Час вийшов, ніхто не відповів!\n{answer_details(question)}"


def format_answered(numbers):
    if not numbers:
        return "Ото лінива срака! На жодне питання ще не відповіли ("
    return "Ви вже відповіли на наступні питання:\n" + "".join(f"{number}," for number in numbers)


def format_leaders(rows, discipline, season):
    lines = [f"Лідери у дисципліні {title(discipline)}, сезон {season}\nvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv\n"]
    for name, answers_count in rows:
        lines.append(f"{name}: {answers_count} вірних відповідей\n==============================\n")
    return "".join(lines)


def format_season_end(discipline, season, winners):
    lines = [f"🏁 Сезон {season} у дисципліні {title(discipline)} завершено! Питання закінчились.\n"]
    if winners:
        lines.append("Переможці:\n")
        lines.extend(f"{iq.PRIZES.get(place, '')}{name}: {count}\n" for place, (name, count) in enumerate(winners, 1))
    else:
        lines.append("Переможців немає, ніхто не відповів правильно (\n")
    lines.append(f"\nПочинаємо сезон {season + 1}!")
    return "".join(lines)


def format_disciplines(current):
    lines = ["Дисципліни вікторини:\n"]
    for code, discipline in DISCIPLINES.items():
        marker = "👉 " if code == current else ""
        lines.append(f"{marker}{code}: {discipline.title} ({len(discipline.questions)} питань)\n")
    lines.append("\nЗмінити (тільки адміни чату): /discipline <код>")
    return "".join(lines)
