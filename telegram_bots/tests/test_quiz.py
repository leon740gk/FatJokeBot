import pytest

from telegram_bots.bots.fat_joke.db import quiz as quiz_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.services import quiz
from telegram_bots.bots.fat_joke.services.quiz import Outcome
from telegram_bots.tests.conftest import FakeRandom, make_user


@pytest.mark.parametrize("discipline", list(quiz.DISCIPLINES))
def test_every_question_has_four_options_and_a_correct_one(discipline):
    for number in quiz.DISCIPLINES[discipline][1]:
        question = quiz.get_question(discipline, number)
        assert len(question.options) == 4, (discipline, number)
        assert any(is_correct for _, is_correct in question.options), (discipline, number)


def test_callback_data_round_trip_and_fits_telegram_limit():
    question = quiz.get_question("mlbb", 100)
    data = quiz.option_callback_data(question, 3)
    assert quiz.parse_callback(data) == quiz.ParsedAnswer("mlbb", 100, 3)
    assert len(data.encode()) <= 64


@pytest.mark.parametrize("data", [None, "", "x", "correct 2", "q mlbb 5", "q nope 5 1", "q mlbb 999 1", "q mlbb 5 4"])
def test_parse_callback_rejects_garbage(data):
    assert quiz.parse_callback(data) is None


def correct_and_wrong_option(discipline, number):
    options = quiz.get_question(discipline, number).options
    correct = next(i for i, (_, ok) in enumerate(options) if ok)
    wrong = next(i for i, (_, ok) in enumerate(options) if not ok)
    return correct, wrong


@pytest.fixture
def player(db):
    users_db.register(db, make_user(1, "Alex"))
    return 1


def ask(db, message_id, discipline="mlbb", number=5):
    quiz_db.save_quiz_message(db, -100, message_id, discipline, number)


def answer(db, user_id, message_id, discipline, number, option):
    return quiz.process_answer(db, user_id, -100, message_id, f"q {discipline} {number} {option}")


def iq_of(db, user_id):
    return users_db.get_iq_and_name(db, user_id)[0]


def test_correct_answer_raises_iq(db, player):
    correct, _ = correct_and_wrong_option("mlbb", 5)
    ask(db, 1)
    result = answer(db, player, 1, "mlbb", 5, correct)
    assert result.outcome is Outcome.CORRECT and "101" in result.text
    assert iq_of(db, player) == 101


def test_wrong_answer_is_remembered(db, player):
    correct, wrong = correct_and_wrong_option("mlbb", 5)
    ask(db, 1)
    assert answer(db, player, 1, "mlbb", 5, wrong).outcome is Outcome.WRONG
    ask(db, 2)
    assert answer(db, player, 2, "mlbb", 5, correct).outcome is Outcome.CHEATER
    assert iq_of(db, player) == 99


def test_same_number_in_other_discipline_is_not_cheating(db, player):
    ask(db, 1, "mlbb", 6)
    answer(db, player, 1, "mlbb", 6, correct_and_wrong_option("mlbb", 6)[0])
    ask(db, 2, "geo", 6)
    assert answer(db, player, 2, "geo", 6, correct_and_wrong_option("geo", 6)[0]).outcome is Outcome.CORRECT


def test_only_first_answer_on_a_message_counts(db, player):
    users_db.register(db, make_user(2, "Bob"))
    correct, _ = correct_and_wrong_option("mlbb", 5)
    ask(db, 1)
    assert answer(db, player, 1, "mlbb", 5, correct).outcome is Outcome.CORRECT
    assert answer(db, 2, 1, "mlbb", 5, correct).outcome is Outcome.CLOSED
    assert iq_of(db, 2) == 100


def test_unknown_message_and_mismatched_button_are_closed(db, player):
    assert answer(db, player, 1, "mlbb", 5, 0).outcome is Outcome.CLOSED
    ask(db, 1, "mlbb", 5)
    assert answer(db, player, 1, "mlbb", 6, 0).outcome is Outcome.CLOSED
    assert iq_of(db, player) == 100


def test_pick_question_uses_current_discipline():
    question = quiz.pick_question(rng=FakeRandom())
    assert question.discipline == quiz.CURRENT_DISCIPLINE and question.number == 1
    assert quiz.question_message_text(question).startswith("MLBB.\n")


def test_formatting():
    assert quiz.format_answered([]).startswith("Ото лінива срака")
    assert quiz.format_answered([3, 7]).endswith("3,7,")
    leaders = quiz.format_leaders([("B", 2), ("A", 1)])
    assert leaders.startswith("Лідери у дисципліні MLBB.") and "B: 2 вірних" in leaders
