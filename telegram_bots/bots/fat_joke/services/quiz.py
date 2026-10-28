import random
from dataclasses import dataclass
from enum import Enum

from telegram_bots.bots.fat_joke.db import quiz as quiz_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.services import iq
from telegram_bots.knowledge_base.fat_joke.test_your_mind.biology.qa_data import questionnaire as bio_q
from telegram_bots.knowledge_base.fat_joke.test_your_mind.geography.qa_data import questionnaire as geo_q
from telegram_bots.knowledge_base.fat_joke.test_your_mind.mlbb.qa_data import questionnaire as mlbb_q
from telegram_bots.knowledge_base.fat_joke.test_your_mind.new_qa.qa_data import questionnaire as general_q
from telegram_bots.knowledge_base.fat_joke.test_your_mind.ukr_language.qa_data import questionnaire as ukr_lang_q

# short codes go into callback_data, so question numbers from different disciplines don't collide
DISCIPLINES = {
    "ukr": ("Українська мова.", ukr_lang_q),
    "geo": ("Географія.", geo_q),
    "bio": ("Біологія.", bio_q),
    "mix": ("Мікс питань.", general_q),
    "mlbb": ("MLBB.", mlbb_q),
}
CURRENT_DISCIPLINE = "mlbb"
OPTION_KEYS = ("1", "2", "3", "4")


@dataclass(frozen=True)
class Question:
    discipline: str
    number: int
    text: str
    options: tuple  # (button label, is_correct) for each option


@dataclass(frozen=True)
class ParsedAnswer:
    discipline: str
    number: int
    option_index: int


class Outcome(Enum):
    CLOSED = "closed"  # old button, or someone has already answered this message
    CHEATER = "cheater"
    CORRECT = "correct"
    WRONG = "wrong"


@dataclass(frozen=True)
class AnswerResult:
    outcome: Outcome
    text: str = ""


def discipline_title(discipline):
    return DISCIPLINES[discipline][0]


def get_question(discipline, number):
    if discipline not in DISCIPLINES:
        return None
    question_dict = DISCIPLINES[discipline][1].get(number)
    if not question_dict:
        return None
    ((text, answers),) = question_dict.items()
    # anything but "correct N" is a wrong option, including the "х"/"ч" typos in the data
    options = tuple((answers[key][0], answers[key][1].startswith("correct")) for key in OPTION_KEYS)
    return Question(discipline, number, text, options)


def pick_question(discipline=CURRENT_DISCIPLINE, rng=random):
    number = rng.choice(list(DISCIPLINES[discipline][1]))
    return get_question(discipline, number)


def question_message_text(question):
    return f"{discipline_title(question.discipline)}\n{question.text}"


def option_callback_data(question, option_index):
    return f"q {question.discipline} {question.number} {option_index}"


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


def process_answer(db, user_id, chat_id, message_id, callback_data):
    parsed = parse_callback(callback_data)
    if not parsed:
        return AnswerResult(Outcome.CLOSED)
    if not quiz_db.claim_quiz_message(db, chat_id, message_id, parsed.discipline, parsed.number, user_id):
        return AnswerResult(Outcome.CLOSED)

    # correctness comes from the question bank, not from the button, so it can't be forged
    is_correct = get_question(parsed.discipline, parsed.number).options[parsed.option_index][1]
    iq_old, user_name = users_db.get_iq_and_name(db, user_id)
    if not quiz_db.save_answer(db, user_id, parsed.discipline, parsed.number, is_correct):
        return AnswerResult(Outcome.CHEATER, iq.anti_cheat_message(user_name))

    iq_new, message = iq.change_message(iq_old, user_name, increase=is_correct)
    users_db.set_iq(db, user_id, iq_new)
    return AnswerResult(Outcome.CORRECT if is_correct else Outcome.WRONG, message)


def format_answered(numbers):
    if not numbers:
        return "Ото лінива срака! На жодне питання ще не відповіли ("
    return "Ви вже відповіли на наступні питання:\n" + "".join(f"{number}," for number in numbers)


def format_leaders(rows, discipline=CURRENT_DISCIPLINE):
    lines = [f"Лідери у дисципліні {discipline_title(discipline)}\nvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv\n"]
    for name, answers_count in rows:
        lines.append(f"{name}: {answers_count} вірних відповідей\n==============================\n")
    return "".join(lines)
