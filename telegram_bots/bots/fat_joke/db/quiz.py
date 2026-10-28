LEGACY_DISCIPLINE = "legacy"


def save_quiz_message(db, chat_id, message_id, discipline, question_number):
    db.execute(
        "INSERT INTO QuizMessages (chat_id, message_id, discipline, question_number) VALUES (?, ?, ?, ?)",
        (chat_id, message_id, discipline, question_number),
    )


def claim_quiz_message(db, chat_id, message_id, discipline, question_number, user_id):
    """Marks the question message as answered by user_id. Only the first claim wins."""
    claimed_rows = db.execute(
        """
        UPDATE QuizMessages SET answered_by = ?
        WHERE chat_id = ? AND message_id = ? AND discipline = ? AND question_number = ? AND answered_by IS NULL
        """,
        (user_id, chat_id, message_id, discipline, question_number),
    )
    return claimed_rows == 1


def save_answer(db, user_id, discipline, question_number, is_correct):
    """Returns False if the user has already answered this question, right or wrong."""
    inserted_rows = db.execute(
        """
        INSERT OR IGNORE INTO Answers (telegram_id, discipline, question_number, is_correct)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, discipline, question_number, int(is_correct)),
    )
    return inserted_rows == 1


def get_answered_numbers(db, user_id, discipline):
    rows = db.fetch_all(
        "SELECT question_number FROM Answers WHERE telegram_id = ? AND discipline = ? ORDER BY question_number",
        (user_id, discipline),
    )
    return [row[0] for row in rows]


def get_leaders(db, discipline, limit=3):
    return db.fetch_all(
        """
        SELECT Users.name, COUNT(*) AS answers_count FROM Answers
        JOIN Users ON Users.telegram_id = Answers.telegram_id
        WHERE Answers.discipline = ? AND Answers.is_correct = 1
        GROUP BY Answers.telegram_id
        ORDER BY answers_count DESC
        LIMIT ?
        """,
        (discipline, limit),
    )
