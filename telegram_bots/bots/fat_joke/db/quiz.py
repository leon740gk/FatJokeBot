LEGACY_DISCIPLINE = "legacy"


def current_season(db, discipline):
    row = db.fetch_one(
        "SELECT number FROM Seasons WHERE discipline = ? AND finished_at IS NULL ORDER BY number DESC LIMIT 1",
        (discipline,),
    )
    if row:
        return row[0]
    last = db.fetch_one("SELECT MAX(number) FROM Seasons WHERE discipline = ?", (discipline,))[0] or 0
    db.execute("INSERT INTO Seasons (discipline, number) VALUES (?, ?)", (discipline, last + 1))
    return last + 1


def finish_season(db, discipline, season):
    db.execute(
        "UPDATE Seasons SET finished_at = CURRENT_TIMESTAMP WHERE discipline = ? AND number = ?", (discipline, season)
    )


def get_asked_numbers(db, discipline, season):
    rows = db.fetch_all(
        "SELECT question_number FROM QuizMessages WHERE discipline = ? AND season = ?", (discipline, season)
    )
    return {row[0] for row in rows}


def save_quiz_message(db, chat_id, message_id, discipline, season, question_number, asked_by=None):
    """asked_by is who called the question with /quiz, only they can answer it; None for scheduled ones."""
    db.execute(
        """
        INSERT INTO QuizMessages (chat_id, message_id, discipline, season, question_number, asked_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (chat_id, message_id, discipline, season, question_number, asked_by),
    )


def get_open_question(db, chat_id, discipline=None):
    """An unanswered question in the chat that is still open, of one discipline or of any."""
    query = "SELECT message_id FROM QuizMessages WHERE chat_id = ? AND answered_by IS NULL AND closed_at IS NULL"
    if discipline is None:
        return db.fetch_one(query, (chat_id,))
    return db.fetch_one(query + " AND discipline = ?", (chat_id, discipline))


def get_open_question_of(db, chat_id, user_id):
    """The user's own unanswered question in the chat that is still open."""
    return db.fetch_one(
        """
        SELECT message_id FROM QuizMessages
        WHERE chat_id = ? AND asked_by = ? AND answered_by IS NULL AND closed_at IS NULL
        """,
        (chat_id, user_id),
    )


def get_open_owner(db, chat_id, message_id):
    """Who called this question, if it is still open and has an owner."""
    row = db.fetch_one(
        """
        SELECT asked_by FROM QuizMessages
        WHERE chat_id = ? AND message_id = ? AND answered_by IS NULL AND closed_at IS NULL
        """,
        (chat_id, message_id),
    )
    return row[0] if row else None


def is_quiz_message(db, chat_id, message_id):
    return (
        db.fetch_one("SELECT 1 FROM QuizMessages WHERE chat_id = ? AND message_id = ?", (chat_id, message_id))
        is not None
    )


def claim_quiz_message(db, chat_id, message_id, discipline, question_number, user_id):
    """Marks the question message as answered by user_id and returns its season, or None if it's closed.

    Only the first claim wins, and only the owner can claim a question someone called for themselves.
    """
    claimed_rows = db.execute(
        """
        UPDATE QuizMessages SET answered_by = ?, closed_at = CURRENT_TIMESTAMP
        WHERE chat_id = ? AND message_id = ? AND discipline = ? AND question_number = ?
          AND answered_by IS NULL AND closed_at IS NULL AND (asked_by IS NULL OR asked_by = ?)
        """,
        (user_id, chat_id, message_id, discipline, question_number, user_id),
    )
    if claimed_rows != 1:
        return None
    return db.fetch_one("SELECT season FROM QuizMessages WHERE chat_id = ? AND message_id = ?", (chat_id, message_id))[
        0
    ]


def close_expired(db, minutes):
    """Closes questions nobody answered in time and returns (chat_id, message_id, discipline, question_number)."""
    expired = db.fetch_all(
        """
        SELECT id, chat_id, message_id, discipline, question_number FROM QuizMessages
        WHERE answered_by IS NULL AND closed_at IS NULL AND created_at <= datetime('now', ?)
        """,
        (f"-{minutes} minutes",),
    )
    for row in expired:
        db.execute("UPDATE QuizMessages SET closed_at = CURRENT_TIMESTAMP WHERE id = ?", (row[0],))
    return [row[1:] for row in expired]


def save_answer(db, user_id, discipline, season, question_number, is_correct):
    """Returns False if the user has already answered this question in this season, right or wrong."""
    inserted_rows = db.execute(
        """
        INSERT OR IGNORE INTO Answers (telegram_id, discipline, season, question_number, is_correct)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, discipline, season, question_number, int(is_correct)),
    )
    return inserted_rows == 1


def get_answered_numbers(db, user_id, discipline, season):
    rows = db.fetch_all(
        """
        SELECT question_number FROM Answers
        WHERE telegram_id = ? AND discipline = ? AND season = ?
        ORDER BY question_number
        """,
        (user_id, discipline, season),
    )
    return [row[0] for row in rows]


def get_leaders(db, discipline, season, limit=3):
    return db.fetch_all(
        """
        SELECT Users.name, COUNT(*) AS answers_count FROM Answers
        JOIN Users ON Users.telegram_id = Answers.telegram_id
        WHERE Answers.discipline = ? AND Answers.season = ? AND Answers.is_correct = 1
        GROUP BY Answers.telegram_id
        ORDER BY answers_count DESC
        LIMIT ?
        """,
        (discipline, season, limit),
    )
