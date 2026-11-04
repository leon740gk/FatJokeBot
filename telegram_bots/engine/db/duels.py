"""Duels: pending (challenge sent) -> active (question asked) -> done; or declined / expired."""

COLUMNS = (
    "id, chat_id, message_id, challenger, opponent, discipline, question_number, status, started_at, "
    "challenger_option, challenger_seconds, opponent_option, opponent_seconds"
)


def create(db, chat_id, challenger, opponent, discipline):
    db.execute(
        "INSERT INTO Duels (chat_id, challenger, opponent, discipline) VALUES (?, ?, ?, ?)",
        (chat_id, challenger, opponent, discipline),
    )
    return db.fetch_one("SELECT last_insert_rowid()")[0]


def set_message(db, duel_id, message_id):
    db.execute("UPDATE Duels SET message_id = ? WHERE id = ?", (message_id, duel_id))


def get(db, duel_id):
    return db.fetch_one(f"SELECT {COLUMNS} FROM Duels WHERE id = ?", (duel_id,))


def open_for(db, chat_id, user_id):
    """id of an unfinished duel in the chat the user takes part in, or None."""
    row = db.fetch_one(
        """
        SELECT id FROM Duels
        WHERE chat_id = ? AND status IN ('pending', 'active') AND ? IN (challenger, opponent)
        """,
        (chat_id, user_id),
    )
    return row[0] if row else None


def set_status(db, duel_id, old, new):
    """Returns False if the duel was no longer `old`, e.g. two presses at once."""
    return db.execute("UPDATE Duels SET status = ? WHERE id = ? AND status = ?", (new, duel_id, old)) == 1


def start(db, duel_id, question_number, discipline, started_at):
    changed = db.execute(
        """
        UPDATE Duels SET status = 'active', question_number = ?, discipline = ?, started_at = ?
        WHERE id = ? AND status = 'pending'
        """,
        (question_number, discipline, started_at, duel_id),
    )
    return changed == 1


def save_answer(db, duel_id, side, option, seconds):
    """side is "challenger" or "opponent"; returns False if that side has already answered."""
    changed = db.execute(
        f"UPDATE Duels SET {side}_option = ?, {side}_seconds = ? WHERE id = ? AND status = 'active' "
        f"AND {side}_option IS NULL",
        (option, seconds, duel_id),
    )
    return changed == 1


def finish(db, duel_id, winner, points):
    changed = db.execute(
        "UPDATE Duels SET status = 'done', winner = ?, points = ? WHERE id = ? AND status = 'active'",
        (winner, points, duel_id),
    )
    return changed == 1


def stale(db, accept_minutes, started_before):
    """(expired pending duels, active duels asked before `started_before`), each as full rows."""
    pending = db.fetch_all(
        f"SELECT {COLUMNS} FROM Duels WHERE status = 'pending' AND created_at <= datetime('now', ?)",
        (f"-{accept_minutes} minutes",),
    )
    active = db.fetch_all(f"SELECT {COLUMNS} FROM Duels WHERE status = 'active' AND started_at <= ?", (started_before,))
    return pending, active


def wins(db, user_id):
    return db.fetch_one("SELECT COUNT(*) FROM Duels WHERE winner = ?", (user_id,))[0]


def points(db, user_id):
    return db.fetch_one("SELECT COALESCE(SUM(points), 0) FROM Duels WHERE winner = ?", (user_id,))[0]
