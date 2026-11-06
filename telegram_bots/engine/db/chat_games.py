"""The chat games that need no quiz: "Це чи те" polls, the question of the day, riddles, and the anonymous messages."""

import time


def used_this_or_that(db, chat_id):
    return {row[0] for row in db.fetch_all("SELECT number FROM ThisOrThat WHERE chat_id = ?", (chat_id,))}


def save_this_or_that(db, chat_id, message_id, number):
    db.execute("INSERT INTO ThisOrThat (chat_id, message_id, number) VALUES (?, ?, ?)", (chat_id, message_id, number))


def used_daily_questions(db, chat_id):
    return {row[0] for row in db.fetch_all("SELECT number FROM DailyQuestions WHERE chat_id = ?", (chat_id,))}


def save_daily_question(db, chat_id, message_id, number):
    db.execute(
        "INSERT INTO DailyQuestions (chat_id, message_id, number) VALUES (?, ?, ?)", (chat_id, message_id, number)
    )


def daily_question_id(db, chat_id, message_id):
    row = db.fetch_one("SELECT id FROM DailyQuestions WHERE chat_id = ? AND message_id = ?", (chat_id, message_id))
    return row[0] if row else None


def answer_daily_question(db, question_id, user_id, points):
    """Returns False if the user has already answered this question: XP only for the first answer."""
    inserted_rows = db.execute(
        "INSERT OR IGNORE INTO DailyAnswers (question_id, telegram_id, points) VALUES (?, ?, ?)",
        (question_id, user_id, points),
    )
    return inserted_rows == 1


def used_riddles(db, chat_id):
    return {row[0] for row in db.fetch_all("SELECT number FROM Riddles WHERE chat_id = ?", (chat_id,))}


def create_riddle(db, chat_id, message_id, number, started_at=None):
    db.execute(
        "INSERT INTO Riddles (chat_id, message_id, number, started_at) VALUES (?, ?, ?, ?)",
        (chat_id, message_id, number, time.time() if started_at is None else started_at),
    )


def open_riddle(db, chat_id):
    """(id, message_id, number, hints_shown) of the riddle still open in the chat, or None."""
    return db.fetch_one(
        "SELECT id, message_id, number, hints_shown FROM Riddles WHERE chat_id = ? AND closed_at IS NULL", (chat_id,)
    )


def all_open_riddles(db):
    """(id, chat_id, message_id, number, started_at, hints_shown) of every open riddle."""
    return db.fetch_all(
        "SELECT id, chat_id, message_id, number, started_at, hints_shown FROM Riddles WHERE closed_at IS NULL"
    )


def set_hints_shown(db, riddle_id, hints_shown):
    db.execute("UPDATE Riddles SET hints_shown = ? WHERE id = ?", (hints_shown, riddle_id))


def solve_riddle(db, riddle_id, user_id, points):
    """Returns False if the riddle is closed already, e.g. someone was a moment faster."""
    changed_rows = db.execute(
        """
        UPDATE Riddles SET solved_by = ?, points = ?, closed_at = CURRENT_TIMESTAMP
        WHERE id = ? AND closed_at IS NULL
        """,
        (user_id, points, riddle_id),
    )
    return changed_rows == 1


def close_riddle(db, riddle_id):
    changed_rows = db.execute(
        "UPDATE Riddles SET closed_at = CURRENT_TIMESTAMP WHERE id = ? AND closed_at IS NULL", (riddle_id,)
    )
    return changed_rows == 1


def points(db, user_id):
    """XP from solved riddles and answers to the question of the day."""
    riddles = db.fetch_one("SELECT COALESCE(SUM(points), 0) FROM Riddles WHERE solved_by = ?", (user_id,))[0]
    answers = db.fetch_one("SELECT COALESCE(SUM(points), 0) FROM DailyAnswers WHERE telegram_id = ?", (user_id,))[0]
    return riddles + answers


def anon_sent_on(db, user_id, day):
    return db.fetch_one("SELECT COUNT(*) FROM AnonMessages WHERE telegram_id = ? AND day = ?", (user_id, day))[0]


def save_anon(db, user_id, day, chat_id, message_id):
    """Only who and when, for the daily limit; the text itself is not kept."""
    db.execute(
        "INSERT INTO AnonMessages (telegram_id, day, chat_id, message_id) VALUES (?, ?, ?, ?)",
        (user_id, day, chat_id, message_id),
    )
