from telegram_bots.engine.db.quiz import LEGACY_DISCIPLINE


def unlocked(db, user_id):
    rows = db.fetch_all("SELECT code FROM Achievements WHERE telegram_id = ? ORDER BY unlocked_at, rowid", (user_id,))
    return [row[0] for row in rows]


def unlock(db, user_id, code):
    """Returns False if the user already has it."""
    inserted_rows = db.execute("INSERT OR IGNORE INTO Achievements (telegram_id, code) VALUES (?, ?)", (user_id, code))
    return inserted_rows == 1


def correct_answers(db, user_id):
    return db.fetch_one("SELECT COUNT(*) FROM Answers WHERE telegram_id = ? AND is_correct = 1", (user_id,))[0]


def answer_results(db, user_id):
    """Right (1) or wrong (0) of every quiz answer in the order given; legacy answers were all right, so not here."""
    rows = db.fetch_all(
        "SELECT is_correct FROM Answers WHERE telegram_id = ? AND discipline != ? ORDER BY id",
        (user_id, LEGACY_DISCIPLINE),
    )
    return [row[0] for row in rows]


def fat_days(db, user_id):
    return db.fetch_one("SELECT COUNT(*) FROM FatDays WHERE telegram_id = ?", (user_id,))[0]


def parties(db, user_id):
    return db.fetch_one("SELECT COUNT(*) FROM PartyMembers WHERE telegram_id = ?", (user_id,))[0]


def quotes_authored(db, user_id):
    return db.fetch_one("SELECT COUNT(*) FROM Quotes WHERE author_id = ?", (user_id,))[0]
