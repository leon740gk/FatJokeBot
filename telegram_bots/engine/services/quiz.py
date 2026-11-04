import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from zoneinfo import ZoneInfo

from telegram_bots.engine.content import active, kb, quiz_dir
from telegram_bots.engine.db import quiz as quiz_db
from telegram_bots.engine.db import settings
from telegram_bots.engine.db import users as users_db
from telegram_bots.engine.services import iq
from telegram_bots.engine.services.quiz_bank import load_disciplines
from telegram_bots.engine.services.topics import resolve_discipline
from telegram_bots.engine.services.words import plural

KYIV = ZoneInfo("Europe/Kyiv")
DISCIPLINE_SETTING = "quiz_discipline"
# longest option that still fits on a button: two buttons per row, or one per row
SHORT_OPTION = 14
BUTTON_OPTION = 30


class Outcome(Enum):
    CLOSED = "closed"  # old button, time is up, or someone has already answered this message
    NOT_YOURS = "not_yours"  # someone else called this question, text is their name
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


_disciplines = {}


def disciplines():
    """{code: Discipline} of the running bot, loaded from its quiz folder once."""
    if active() not in _disciplines:
        _disciplines[active()] = load_disciplines(quiz_dir())
    return _disciplines[active()]


def default_discipline():
    """The topic of scheduled questions until an admin picks another with /discipline."""
    code = kb.theme_data.default_discipline
    return code if code in disciplines() else next(iter(disciplines()))


def current_discipline(db):
    code = settings.get(db, DISCIPLINE_SETTING)
    return code if code in disciplines() else default_discipline()


def set_discipline(db, code):
    settings.set_value(db, DISCIPLINE_SETTING, code)


def title(code):
    return disciplines()[code].title


def find_discipline(text):
    return resolve_discipline(text, disciplines())


def topic_callback_data(code, owner_id=None):
    return f"t {code} {owner_id}" if owner_id else f"t {code}"


def parse_topic_callback(data):
    """(discipline, who may pick it or None for anyone), or None; "t <code> [<owner id>]"."""
    parts = (data or "").split(" ")
    if len(parts) not in (2, 3) or parts[0] != "t" or parts[1] not in disciplines():
        return None
    if len(parts) == 2:
        return parts[1], None
    return (parts[1], int(parts[2])) if parts[2].isdigit() else None


def kyiv_day_start(now=None):
    """Start of today in Kyiv as UTC "YYYY-MM-DD HH:MM:SS", the way SQLite's CURRENT_TIMESTAMP stores times."""
    now = (now or datetime.now(UTC)).astimezone(KYIV)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def limit_reached(db, user_id, limit, now=None):
    """limit is /quiz questions a day per person, 0 means no limit."""
    return bool(limit) and quiz_db.count_asked_by(db, user_id, kyiv_day_start(now)) >= limit


def limit_text(limit):
    return kb.texts.quiz_limit.format(limit=limit, questions=plural(limit, *kb.texts.question_forms))


def render_topic_picker(owner_id=None):
    """Buttons with all disciplines for "/quiz" without a topic, two per row; only owner_id may press them."""
    buttons = [(discipline.title, topic_callback_data(code, owner_id)) for code, discipline in disciplines().items()]
    return RenderedQuestion(kb.texts.quiz_pick_topic, [buttons[i : i + 2] for i in range(0, len(buttons), 2)])


def get_question(discipline, number):
    if discipline not in disciplines():
        return None
    return disciplines()[discipline].questions.get(number)


def pick_question(db, discipline, rng=random):
    """Picks a question nobody has been asked this season; starts a new season when they run out."""
    season = quiz_db.current_season(db, discipline)
    asked = quiz_db.get_asked_numbers(db, discipline, season)
    numbers = [number for number in disciplines()[discipline].questions if number not in asked]
    if numbers:
        return PickResult(get_question(discipline, rng.choice(numbers)), season)

    winners = quiz_db.get_leaders(db, discipline, season)
    quiz_db.finish_season(db, discipline, season)
    new_season = quiz_db.current_season(db, discipline)
    question = get_question(discipline, rng.choice(list(disciplines()[discipline].questions)))
    return PickResult(question, new_season, finished_season=season, winners=winners)


def option_callback_data(question, option_index):
    return f"q {question.discipline} {question.number} {option_index}"


def render_question(question, rng=random):
    order = list(range(len(question.options)))
    if disciplines()[question.discipline].shuffle_options:
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
    details = kb.texts.quiz_right_answer.format(answer=correct)
    if question.explanation:
        details += f"\n{question.explanation}"
    return details


def process_answer(db, user_id, chat_id, message_id, callback_data):
    parsed = parse_callback(callback_data)
    if not parsed:
        return AnswerResult(Outcome.CLOSED)
    owner = quiz_db.get_open_owner(db, chat_id, message_id)
    if owner and owner != user_id:
        return AnswerResult(Outcome.NOT_YOURS, users_db.get_iq_and_name(db, owner)[1])
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
    return f"{header}\n\n{kb.texts.quiz_expired}\n{answer_details(question)}"


def format_answered(numbers):
    if not numbers:
        return kb.texts.answered_none
    return kb.texts.answered_title + "".join(f"{number}," for number in numbers)


def format_leaders(rows, discipline, season):
    lines = [kb.texts.leaders_title.format(topic=title(discipline), season=season)]
    for name, answers_count in rows:
        lines.append(kb.texts.leaders_row.format(name=name, count=answers_count))
    return "".join(lines)


def format_all_leaders(rows):
    """rows of (discipline, season, leaders) for every topic; topics nobody has answered go to one line."""
    lines = [kb.texts.all_leaders_title]
    empty = []
    for discipline, season, leaders in rows:
        if not leaders:
            empty.append(title(discipline))
            continue
        lines.append(kb.texts.all_leaders_topic.format(topic=title(discipline), season=season))
        lines.extend(f"{iq.PRIZES[place]} {name} — {count}" for place, (name, count) in enumerate(leaders, start=1))
    if empty:
        lines.append(kb.texts.all_leaders_empty.format(topics=", ".join(empty)))
    lines.append(kb.texts.all_leaders_footer)
    return "\n".join(lines)


def format_season_end(discipline, season, winners):
    lines = [kb.texts.season_end.format(season=season, topic=title(discipline))]
    if winners:
        lines.append(kb.texts.season_winners)
        lines.extend(f"{iq.PRIZES.get(place, '')}{name}: {count}\n" for place, (name, count) in enumerate(winners, 1))
    else:
        lines.append(kb.texts.season_no_winners)
    lines.append(kb.texts.season_next.format(season=season + 1))
    return "".join(lines)


def format_disciplines(current):
    lines = [kb.texts.disciplines_title]
    for code, discipline in disciplines().items():
        marker = "👉 " if code == current else ""
        count = len(discipline.questions)
        lines.append(
            kb.texts.disciplines_row.format(
                marker=marker,
                code=code,
                title=discipline.title,
                count=count,
                questions=plural(count, *kb.texts.question_forms),
            )
        )
    lines.append(kb.texts.disciplines_footer)
    return "".join(lines)
