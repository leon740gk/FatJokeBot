def save(db, chat_id, message_id, author_id, author_name, author_username, text, said_on, saved_by):
    """Returns False if this message is already in the quote book."""
    inserted_rows = db.execute(
        """
        INSERT OR IGNORE INTO Quotes
            (chat_id, message_id, author_id, author_name, author_username, text, said_on, saved_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (chat_id, message_id, author_id, author_name, author_username, text, said_on, saved_by),
    )
    return inserted_rows == 1


def count(db, chat_id):
    return db.fetch_one("SELECT COUNT(*) FROM Quotes WHERE chat_id = ?", (chat_id,))[0]


def get_all(db, chat_id):
    """(text, author_name, author_username, said_on) of every quote in the chat."""
    return db.fetch_all(
        "SELECT text, author_name, author_username, said_on FROM Quotes WHERE chat_id = ? ORDER BY id", (chat_id,)
    )


def take_least_shown(db, chat_id):
    """The quote shown longest ago (never shown ones first) for the quote of the day; marks it as shown."""
    row = db.fetch_one(
        """
        SELECT id, text, author_name, author_username, said_on FROM Quotes WHERE chat_id = ?
        ORDER BY shown_at IS NOT NULL, shown_at, RANDOM() LIMIT 1
        """,
        (chat_id,),
    )
    if not row:
        return None
    db.execute("UPDATE Quotes SET shown_at = CURRENT_TIMESTAMP WHERE id = ?", (row[0],))
    return row[1:]
