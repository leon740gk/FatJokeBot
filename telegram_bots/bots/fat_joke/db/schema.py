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
    DOB TEXT,
    in_chat INTEGER NOT NULL DEFAULT 1
)
"""

ANSWERS_TABLE = """
CREATE TABLE IF NOT EXISTS Answers (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER NOT NULL,
    discipline TEXT NOT NULL,
    question_number INTEGER NOT NULL,
    is_correct INTEGER NOT NULL,
    season INTEGER NOT NULL DEFAULT 1,
    answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (telegram_id, discipline, season, question_number)
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
    season INTEGER NOT NULL DEFAULT 1,
    closed_at TEXT,
    UNIQUE (chat_id, message_id)
)
"""

SEASONS_TABLE = """
CREATE TABLE IF NOT EXISTS Seasons (
    discipline TEXT NOT NULL,
    number INTEGER NOT NULL,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    PRIMARY KEY (discipline, number)
)
"""

SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS Settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
"""


QUOTES_TABLE = """
CREATE TABLE IF NOT EXISTS Quotes (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    author_id INTEGER,
    author_name TEXT NOT NULL,
    author_username TEXT,
    text TEXT NOT NULL,
    said_on TEXT NOT NULL,
    saved_by INTEGER NOT NULL,
    saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
    shown_at TEXT,
    UNIQUE (chat_id, message_id)
)
"""

FAT_DAYS_TABLE = """
CREATE TABLE IF NOT EXISTS FatDays (
    chat_id INTEGER NOT NULL,
    day TEXT NOT NULL,
    telegram_id INTEGER NOT NULL,
    PRIMARY KEY (chat_id, day)
)
"""

PARTIES_TABLE = """
CREATE TABLE IF NOT EXISTS Parties (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    created_by INTEGER NOT NULL,
    comment TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    gathered_at TEXT,
    UNIQUE (chat_id, message_id)
)
"""

PARTY_MEMBERS_TABLE = """
CREATE TABLE IF NOT EXISTS PartyMembers (
    party_id INTEGER NOT NULL,
    telegram_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    username TEXT,
    joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (party_id, telegram_id)
)
"""

TABLES = (
    USERS_TABLE,
    ANSWERS_TABLE,
    QUIZ_MESSAGES_TABLE,
    SEASONS_TABLE,
    SETTINGS_TABLE,
    QUOTES_TABLE,
    FAT_DAYS_TABLE,
    PARTIES_TABLE,
    PARTY_MEMBERS_TABLE,
)


def init_schema(db):
    for table in TABLES:
        db.execute(table)
    _add_seasons_to_old_tables(db)
    _migrate_legacy_answers(db)
    if "in_chat" not in _columns(db, "Users"):
        # added 2026-10-31; everyone counts as a member until /members or a leave says otherwise
        db.execute("ALTER TABLE Users ADD COLUMN in_chat INTEGER NOT NULL DEFAULT 1")


def _columns(db, table):
    return {row[1] for row in db.fetch_all(f"PRAGMA table_info({table})")}


def _add_seasons_to_old_tables(db):
    # tables created before seasons existed (2026-10-28); everything in them belongs to season 1
    if "season" not in _columns(db, "Answers"):
        # the unique key changes too, and SQLite can only do that by rebuilding the table
        db.execute(ANSWERS_TABLE.replace("Answers", "Answers_new"))
        db.execute(
            """
            INSERT INTO Answers_new (id, telegram_id, discipline, question_number, is_correct, answered_at)
            SELECT id, telegram_id, discipline, question_number, is_correct, answered_at FROM Answers
            """
        )
        db.execute("DROP TABLE Answers")
        db.execute("ALTER TABLE Answers_new RENAME TO Answers")
    quiz_message_columns = _columns(db, "QuizMessages")
    if "season" not in quiz_message_columns:
        db.execute("ALTER TABLE QuizMessages ADD COLUMN season INTEGER NOT NULL DEFAULT 1")
    if "closed_at" not in quiz_message_columns:
        db.execute("ALTER TABLE QuizMessages ADD COLUMN closed_at TEXT")
        # old answered questions are closed already
        db.execute("UPDATE QuizMessages SET closed_at = created_at WHERE answered_by IS NOT NULL")


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
