import json

from telegram_bots.bots.fat_joke.db.quiz import LEGACY_DISCIPLINE

USERS_TABLE = """
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    username TEXT,
    iq_level INTEGER,
    last_message_date TEXT,
    activity_delta INTEGER,
    questionare_done TEXT,
    DOB TEXT
)
"""

ANSWERS_TABLE = """
CREATE TABLE IF NOT EXISTS Answers (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER NOT NULL,
    discipline TEXT NOT NULL,
    question_number INTEGER NOT NULL,
    is_correct INTEGER NOT NULL,
    answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (telegram_id, discipline, question_number)
)
"""

QUIZ_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS QuizMessages (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    discipline TEXT NOT NULL,
    question_number INTEGER NOT NULL,
    answered_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (chat_id, message_id)
)
"""


def init_schema(db):
    for table in (USERS_TABLE, ANSWERS_TABLE, QUIZ_MESSAGES_TABLE):
        db.execute(table)
    _migrate_legacy_answers(db)


def _migrate_legacy_answers(db):
    # Users.questionare_done kept bare question numbers without a discipline,
    # so the old correct answers are moved over under a separate "legacy" discipline
    for user_id, questionare_done in db.fetch_all("SELECT telegram_id, questionare_done FROM Users"):
        for question_number in json.loads(questionare_done or "[]"):
            db.execute(
                """
                INSERT OR IGNORE INTO Answers (telegram_id, discipline, question_number, is_correct)
                VALUES (?, ?, ?, 1)
                """,
                (user_id, LEGACY_DISCIPLINE, int(question_number)),
            )
