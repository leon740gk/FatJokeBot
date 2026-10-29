import json
import random

import pytest

from telegram_bots.bots.fat_joke.db import quiz as quiz_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.services import quiz
from telegram_bots.bots.fat_joke.services.quiet_hours import is_quiet, parse_quiet_hours
from telegram_bots.bots.fat_joke.services.quiz import Outcome
from telegram_bots.bots.fat_joke.services.quiz_bank import load_discipline
from telegram_bots.tests.conftest import FakeRandom, make_user


def test_all_disciplines_load():
    assert {"ukr", "geo", "bio", "mix", "mlbb", "mlbb2", "accounting"} <= set(quiz.DISCIPLINES)
    assert len(quiz.DISCIPLINES["accounting"].questions) == 50
    assert len(quiz.DISCIPLINES["mlbb"].questions) == 100
    assert len(quiz.DISCIPLINES["mlbb2"].questions) == 50
    assert quiz.DISCIPLINES["mlbb2"].shuffle_options


def write_discipline(tmp_path, questions, code="test"):
    path = tmp_path / f"{code}.json"
    path.write_text(json.dumps({"code": code, "title": "Test", "questions": questions}), encoding="utf-8")
    return path


GOOD = {"number": 1, "text": "Q?", "options": ["a", "b", "c", "d"], "correct": [1]}


@pytest.mark.parametrize(
    "broken",
    [
        {**GOOD, "options": ["a", "b", "c"]},
        {**GOOD, "correct": []},
        {**GOOD, "correct": [4]},
        {**GOOD, "text": " "},
        {**GOOD, "number": 0},
    ],
)
def test_broken_questions_are_rejected(tmp_path, broken):
    with pytest.raises(ValueError):
        load_discipline(write_discipline(tmp_path, [broken]))


def test_duplicate_numbers_and_wrong_code_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="twice"):
        load_discipline(write_discipline(tmp_path, [GOOD, GOOD]))
    path = write_discipline(tmp_path, [GOOD])
    with pytest.raises(ValueError, match="file name"):
        load_discipline(path.rename(tmp_path / "other.json"))


def test_callback_data_round_trip_and_fits_telegram_limit():
    question = quiz.get_question("mlbb2", 50)
    data = quiz.option_callback_data(question, 3)
    assert quiz.parse_callback(data) == quiz.ParsedAnswer("mlbb2", 50, 3)
    assert (
        max(
            len(quiz.option_callback_data(q, 3).encode())
            for d in quiz.DISCIPLINES.values()
            for q in d.questions.values()
        )
        <= 64
    )


@pytest.mark.parametrize("data", [None, "", "x", "correct 2", "q mlbb 5", "q nope 5 1", "q mlbb 999 1", "q mlbb 5 4"])
def test_parse_callback_rejects_garbage(data):
    assert quiz.parse_callback(data) is None


def test_render_short_options_two_per_row():
    question = quiz.get_question("mlbb2", 4)  # "3", "4", "6", "5"
    rendered = quiz.render_question(question, rng=random.Random(1))
    assert [len(row) for row in rendered.rows] == [2, 2]
    assert sorted(label for row in rendered.rows for label, _ in row) == sorted(question.options)
    assert rendered.text == f"MLBB 2.\n{question.text}"


def test_render_medium_options_one_per_row():
    question = next(q for q in quiz.DISCIPLINES["mlbb2"].questions.values() if 14 < max(map(len, q.options)) <= 30)
    rendered = quiz.render_question(question, rng=random.Random(1))
    assert [len(row) for row in rendered.rows] == [1, 1, 1, 1]
    assert rendered.text == f"MLBB 2.\n{question.text}"


def test_render_long_options_listed_in_text():
    question = quiz.get_question("ukr", 1)
    rendered = quiz.render_question(question, rng=FakeRandom())
    assert "1) п'ятниць, їстоньки, яблунька" in rendered.text
    assert [label for row in rendered.rows for label, _ in row] == ["1", "2", "3", "4"]
    assert [data for row in rendered.rows for _, data in row] == [f"q ukr 1 {i}" for i in range(4)]


def test_shuffle_keeps_original_indexes_in_callbacks():
    question = quiz.get_question("mlbb2", 1)
    rendered = quiz.render_question(question, rng=random.Random(3))
    for row in rendered.rows:
        for label, data in row:
            assert question.options[quiz.parse_callback(data).option_index] == label


def test_old_disciplines_are_not_shuffled():
    question = quiz.get_question("mlbb", 2)
    labels = [label for row in quiz.render_question(question, rng=random.Random(3)).rows for label, _ in row]
    assert labels in (list(question.options), ["1", "2", "3", "4"])


@pytest.fixture
def player(db):
    users_db.register(db, make_user(1, "Alex"))
    return 1


def ask(db, message_id, discipline="mlbb2", number=5, season=1):
    quiz_db.save_quiz_message(db, -100, message_id, discipline, season, number)


def answer(db, user_id, message_id, discipline, number, option):
    return quiz.process_answer(db, user_id, -100, message_id, f"q {discipline} {number} {option}")


def correct_and_wrong(discipline, number):
    question = quiz.get_question(discipline, number)
    wrong = next(i for i in range(4) if i not in question.correct)
    return min(question.correct), wrong


def iq_of(db, user_id):
    return users_db.get_iq_and_name(db, user_id)[0]


def test_correct_answer_raises_iq_and_shows_explanation(db, player):
    correct, _ = correct_and_wrong("mlbb2", 42)
    ask(db, 1, number=42)
    result = answer(db, player, 1, "mlbb2", 42, correct)
    assert result.outcome is Outcome.CORRECT and "101" in result.text
    assert "Правильный ответ: Мьянмы" in result.text and "Кьянзитта" in result.text
    assert iq_of(db, player) == 101


def test_wrong_answer_is_remembered_within_a_season(db, player):
    correct, wrong = correct_and_wrong("mlbb2", 5)
    ask(db, 1)
    assert answer(db, player, 1, "mlbb2", 5, wrong).outcome is Outcome.WRONG
    ask(db, 2)
    assert answer(db, player, 2, "mlbb2", 5, correct).outcome is Outcome.CHEATER
    assert iq_of(db, player) == 99
    ask(db, 3, season=2)
    assert answer(db, player, 3, "mlbb2", 5, correct).outcome is Outcome.CORRECT


def test_all_options_correct_joke_question(db, player):
    ask(db, 1, number=50)
    assert answer(db, player, 1, "mlbb2", 50, 3).outcome is Outcome.CORRECT


def test_same_number_in_other_discipline_is_not_cheating(db, player):
    ask(db, 1, "mlbb", 6)
    answer(db, player, 1, "mlbb", 6, correct_and_wrong("mlbb", 6)[0])
    ask(db, 2, "geo", 6)
    assert answer(db, player, 2, "geo", 6, correct_and_wrong("geo", 6)[0]).outcome is Outcome.CORRECT


def test_only_first_answer_on_a_message_counts(db, player):
    users_db.register(db, make_user(2, "Bob"))
    correct, _ = correct_and_wrong("mlbb2", 5)
    ask(db, 1)
    assert answer(db, player, 1, "mlbb2", 5, correct).outcome is Outcome.CORRECT
    assert answer(db, 2, 1, "mlbb2", 5, correct).outcome is Outcome.CLOSED
    assert iq_of(db, 2) == 100


def test_unknown_message_and_mismatched_button_are_closed(db, player):
    assert answer(db, player, 1, "mlbb2", 5, 0).outcome is Outcome.CLOSED
    ask(db, 1, number=5)
    assert answer(db, player, 1, "mlbb2", 6, 0).outcome is Outcome.CLOSED
    assert iq_of(db, player) == 100


def test_discipline_setting(db):
    assert quiz.current_discipline(db) == "mlbb2"
    quiz.set_discipline(db, "geo")
    assert quiz.current_discipline(db) == "geo"
    quiz.set_discipline(db, "removed-discipline")
    assert quiz.current_discipline(db) == "mlbb2"


def test_questions_do_not_repeat_until_the_season_ends(db, player):
    numbers = set()
    for message_id in range(50):
        picked = quiz.pick_question(db, "mlbb2", rng=random.Random(message_id))
        assert picked.season == 1 and picked.finished_season is None
        numbers.add(picked.question.number)
        ask(db, message_id, number=picked.question.number)
        if message_id == 0:
            answer(db, player, 0, "mlbb2", picked.question.number, min(picked.question.correct))
    assert len(numbers) == 50

    picked = quiz.pick_question(db, "mlbb2", rng=random.Random(0))
    assert (picked.finished_season, picked.season) == (1, 2)
    assert picked.winners == [("Alex", 1)]
    end = quiz.format_season_end("mlbb2", 1, picked.winners)
    assert "Сезон 1" in end and "🥇Alex: 1" in end and "сезон 2" in end


def test_expired_text_reveals_the_answer():
    text = quiz.expired_text(quiz.get_question("mlbb2", 1))
    assert "Время вышло" in text and "Правильный ответ: Moonton" in text


def test_formatting():
    assert quiz.format_answered([]).startswith("Вот ленивая срака")
    assert quiz.format_answered([3, 7]).endswith("3,7,")
    leaders = quiz.format_leaders([("B", 2), ("A", 1)], "mlbb2", 3)
    assert leaders.startswith("Лидеры в дисциплине MLBB 2, сезон 3") and "B: 2 верных" in leaders
    listing = quiz.format_disciplines("mlbb2")
    assert "👉 mlbb2: MLBB 2 (50 вопросов)" in listing and "geo: География" in listing


@pytest.mark.parametrize(
    "value, hour, quiet",
    [("0-8", 0, True), ("0-8", 7, True), ("0-8", 8, False), ("23-7", 23, True), ("23-7", 3, True), ("23-7", 12, False)],
)
def test_quiet_hours(value, hour, quiet):
    assert is_quiet(hour, parse_quiet_hours(value)) is quiet


@pytest.mark.parametrize("value", ["", "abc", "5-5", "0-30", None])
def test_quiet_hours_off(value):
    assert parse_quiet_hours(value) is None
    assert not is_quiet(3, parse_quiet_hours(value))


@pytest.mark.parametrize(
    "text, code",
    [
        ("мобла", "mlbb2"),
        ("хочу вопрос по мобле", "mlbb2"),
        ("MLBB", "mlbb"),
        ("старая мобла", "mlbb"),
        ("по бухгалтерии", "accounting"),
        ("бухгалтерія", "accounting"),
        ("Бухгалтерия", "accounting"),
        ("географии", "geo"),
        ("по українській", "ukr"),
        ("accounting", "accounting"),
        ("ерунда", None),
        ("", None),
        ("мобла бух", None),
    ],
)
def test_find_discipline(text, code):
    assert quiz.find_discipline(text) == code


def test_topic_picker_has_every_discipline():
    picker = quiz.render_topic_picker()
    buttons = [button for row in picker.rows for button in row]
    assert len(buttons) == len(quiz.DISCIPLINES) and all(len(row) <= 2 for row in picker.rows)
    assert {quiz.parse_topic_callback(data) for _, data in buttons} == set(quiz.DISCIPLINES)
    assert quiz.parse_topic_callback("t nope") is None and quiz.parse_topic_callback("q mlbb 1 1") is None


def test_aliases_must_be_strings(tmp_path):
    path = tmp_path / "test.json"
    path.write_text(json.dumps({"code": "test", "title": "T", "aliases": [""], "questions": [GOOD]}), encoding="utf-8")
    with pytest.raises(ValueError, match="aliases"):
        load_discipline(path)
