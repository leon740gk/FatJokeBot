from datetime import datetime

from telegram_bots.bots.fat_joke.db import quiz as quiz_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.db.schema import init_schema
from telegram_bots.tests.conftest import make_user


def test_register_adds_user_once(db):
    users_db.register(db, make_user(1, "Alex", "alex"))
    users_db.register(db, make_user(1, "Renamed", "alex"))
    assert db.fetch_all("SELECT telegram_id, name, username, iq_level FROM Users") == [(1, "Alex", "alex", 100)]


def test_register_falls_back_to_username_and_id(db):
    users_db.register(db, make_user(1, first_name=None, username="nick"))
    users_db.register(db, make_user(2, first_name=None, username=None))
    assert db.fetch_all("SELECT name FROM Users ORDER BY telegram_id") == [("nick",), ("2",)]


def test_activity_deltas(db):
    users_db.register(db, make_user(1))
    users_db.register(db, make_user(2))
    users_db.touch_activity(db, 1, now=datetime(2026, 10, 1, 12, 0))
    users_db.update_activity_deltas(db, now=datetime(2026, 10, 4, 13, 0))
    assert db.fetch_all("SELECT telegram_id, activity_delta FROM Users ORDER BY telegram_id") == [(1, 3), (2, 0)]
    assert [row[2] for row in users_db.get_inactive(db)] == [3]


def test_legacy_answers_migrate_once(db):
    db.execute(
        "INSERT INTO Users (telegram_id, name, iq_level, questionare_done) VALUES (1, 'Old', 120, '[\"5\", \"7\"]')"
    )
    init_schema(db)
    init_schema(db)
    assert db.fetch_all("SELECT discipline, question_number, is_correct FROM Answers ORDER BY question_number") == [
        ("legacy", 5, 1),
        ("legacy", 7, 1),
    ]


def test_save_answer_only_once_per_discipline_question(db):
    assert quiz_db.save_answer(db, 1, "mlbb", 5, is_correct=False)
    assert not quiz_db.save_answer(db, 1, "mlbb", 5, is_correct=True)
    assert quiz_db.save_answer(db, 1, "geo", 5, is_correct=True)


def test_first_claim_wins(db):
    quiz_db.save_quiz_message(db, -100, 10, "mlbb", 5)
    assert quiz_db.claim_quiz_message(db, -100, 10, "mlbb", 5, user_id=1)
    assert not quiz_db.claim_quiz_message(db, -100, 10, "mlbb", 5, user_id=2)


def test_claim_rejects_unknown_or_mismatched_message(db):
    quiz_db.save_quiz_message(db, -100, 10, "mlbb", 5)
    assert not quiz_db.claim_quiz_message(db, -100, 11, "mlbb", 5, user_id=1)
    assert not quiz_db.claim_quiz_message(db, -100, 10, "mlbb", 6, user_id=1)


def test_leaders_count_correct_answers_of_one_discipline(db):
    for user_id, name in [(1, "A"), (2, "B"), (3, "C")]:
        users_db.register(db, make_user(user_id, name))
    quiz_db.save_answer(db, 1, "mlbb", 1, True)
    quiz_db.save_answer(db, 1, "mlbb", 2, False)
    quiz_db.save_answer(db, 2, "mlbb", 1, True)
    quiz_db.save_answer(db, 2, "mlbb", 2, True)
    quiz_db.save_answer(db, 3, "geo", 1, True)
    assert quiz_db.get_leaders(db, "mlbb") == [("B", 2), ("A", 1)]
    assert quiz_db.get_answered_numbers(db, 1, "mlbb") == [1, 2]
