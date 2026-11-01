def create(db, chat_id, message_id, kind, points):
    db.execute(
        "INSERT INTO Loot (chat_id, message_id, kind, points) VALUES (?, ?, ?, ?)", (chat_id, message_id, kind, points)
    )


def find(db, chat_id, message_id):
    """(kind, points, taken_by) of the loot on this message, or None."""
    return db.fetch_one(
        "SELECT kind, points, taken_by FROM Loot WHERE chat_id = ? AND message_id = ?", (chat_id, message_id)
    )


def claim(db, chat_id, message_id, user_id, minutes):
    """Returns False if someone has already taken it or it has been lying for more than `minutes`."""
    changed_rows = db.execute(
        """
        UPDATE Loot SET taken_by = ?, taken_at = CURRENT_TIMESTAMP
        WHERE chat_id = ? AND message_id = ? AND taken_by IS NULL AND created_at > datetime('now', ?)
        """,
        (user_id, chat_id, message_id, f"-{minutes} minutes"),
    )
    return changed_rows == 1


def taken_by_kind(db, user_id):
    """{kind: how many times the user took it}."""
    rows = db.fetch_all("SELECT kind, COUNT(*) FROM Loot WHERE taken_by = ? GROUP BY kind", (user_id,))
    return dict(rows)


def points(db, user_id):
    return db.fetch_one("SELECT COALESCE(SUM(points), 0) FROM Loot WHERE taken_by = ?", (user_id,))[0]
