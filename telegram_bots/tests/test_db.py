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


def test_old_tables_get_seasons(tmp_path):
    from telegram_bots.bots.fat_joke.db.connection import Database

    db = Database(tmp_path / "old.db")
    db.execute("CREATE TABLE Users (id INTEGER PRIMARY KEY, telegram_id INTEGER, name TEXT, questionare_done TEXT)")
    db.execute(
        """CREATE TABLE Answers (id INTEGER PRIMARY KEY, telegram_id INTEGER NOT NULL, discipline TEXT NOT NULL,
        question_number INTEGER NOT NULL, is_correct INTEGER NOT NULL, answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (telegram_id, discipline, question_number))"""
    )
    db.execute(
        """CREATE TABLE QuizMessages (id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, message_id INTEGER NOT NULL,
        discipline TEXT NOT NULL, question_number INTEGER NOT NULL, answered_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE (chat_id, message_id))"""
    )
    db.execute("INSERT INTO Answers (telegram_id, discipline, question_number, is_correct) VALUES (1, 'mlbb', 5, 1)")
    db.execute(
        "INSERT INTO QuizMessages (chat_id, message_id, discipline, question_number, answered_by) "
        "VALUES (1, 1, 'mlbb', 5, 1)"
    )
    db.execute("INSERT INTO QuizMessages (chat_id, message_id, discipline, question_number) VALUES (1, 2, 'mlbb', 6)")
    init_schema(db)
    init_schema(db)
    assert db.fetch_all("SELECT discipline, season, question_number FROM Answers") == [("mlbb", 1, 5)]
    # the same question can be answered again in the next season
    assert quiz_db.save_answer(db, 1, "mlbb", 2, 5, True)
    rows = db.fetch_all("SELECT message_id, season, closed_at IS NOT NULL FROM QuizMessages ORDER BY message_id")
    assert rows == [(1, 1, 1), (2, 1, 0)]
    db.close()


def test_save_answer_only_once_per_question_and_season(db):
    assert quiz_db.save_answer(db, 1, "mlbb", 1, 5, is_correct=False)
    assert not quiz_db.save_answer(db, 1, "mlbb", 1, 5, is_correct=True)
    assert quiz_db.save_answer(db, 1, "geo", 1, 5, is_correct=True)
    assert quiz_db.save_answer(db, 1, "mlbb", 2, 5, is_correct=True)


def test_first_claim_wins_and_closes_the_question(db):
    quiz_db.save_quiz_message(db, -100, 10, "mlbb", 3, 5)
    assert quiz_db.get_open_question(db, -100) == (10,)
    assert quiz_db.claim_quiz_message(db, -100, 10, "mlbb", 5, user_id=1) == 3
    assert quiz_db.claim_quiz_message(db, -100, 10, "mlbb", 5, user_id=2) is None
    assert quiz_db.get_open_question(db, -100) is None


def test_claim_rejects_unknown_or_mismatched_message(db):
    quiz_db.save_quiz_message(db, -100, 10, "mlbb", 1, 5)
    assert quiz_db.claim_quiz_message(db, -100, 11, "mlbb", 5, user_id=1) is None
    assert quiz_db.claim_quiz_message(db, -100, 10, "mlbb", 6, user_id=1) is None


def test_expired_questions_close_and_cannot_be_claimed(db):
    quiz_db.save_quiz_message(db, -100, 10, "mlbb", 1, 5)
    quiz_db.save_quiz_message(db, -100, 11, "mlbb", 1, 6)
    db.execute("UPDATE QuizMessages SET created_at = datetime('now', '-20 minutes') WHERE message_id = 10")
    assert quiz_db.close_expired(db, minutes=15) == [(-100, 10, "mlbb", 5)]
    assert quiz_db.close_expired(db, minutes=15) == []
    assert quiz_db.claim_quiz_message(db, -100, 10, "mlbb", 5, user_id=1) is None
    assert quiz_db.claim_quiz_message(db, -100, 11, "mlbb", 6, user_id=1) == 1


def test_seasons(db):
    assert quiz_db.current_season(db, "mlbb") == 1
    assert quiz_db.current_season(db, "mlbb") == 1
    quiz_db.finish_season(db, "mlbb", 1)
    assert quiz_db.current_season(db, "mlbb") == 2
    assert quiz_db.current_season(db, "geo") == 1


def test_leaders_count_correct_answers_of_one_discipline_and_season(db):
    for user_id, name in [(1, "A"), (2, "B"), (3, "C")]:
        users_db.register(db, make_user(user_id, name))
    quiz_db.save_answer(db, 1, "mlbb", 1, 1, True)
    quiz_db.save_answer(db, 1, "mlbb", 1, 2, False)
    quiz_db.save_answer(db, 2, "mlbb", 1, 1, True)
    quiz_db.save_answer(db, 2, "mlbb", 1, 2, True)
    quiz_db.save_answer(db, 3, "geo", 1, 1, True)
    quiz_db.save_answer(db, 3, "mlbb", 2, 1, True)
    assert quiz_db.get_leaders(db, "mlbb", 1) == [("B", 2), ("A", 1)]
    assert quiz_db.get_answered_numbers(db, 1, "mlbb", 1) == [1, 2]


def test_settings(db):
    from telegram_bots.bots.fat_joke.db import settings

    assert settings.get(db, "x", "default") == "default"
    settings.set_value(db, "x", "1")
    settings.set_value(db, "x", "2")
    assert settings.get(db, "x") == "2"


def test_old_users_get_in_chat_column(tmp_path):
    from telegram_bots.bots.fat_joke.db.connection import Database

    db = Database(tmp_path / "old.db")
    db.execute("CREATE TABLE Users (id INTEGER PRIMARY KEY, telegram_id INTEGER, name TEXT, questionare_done TEXT)")
    db.execute("INSERT INTO Users (telegram_id, name, questionare_done) VALUES (1, 'Old', '[]')")
    init_schema(db)
    init_schema(db)
    assert db.fetch_all("SELECT telegram_id, in_chat FROM Users") == [(1, 1)]
