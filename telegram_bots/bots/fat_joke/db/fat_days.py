def get_winner(db, chat_id, day):
    """(name, username) of the day's fatty in this chat, or None if nobody has been picked yet."""
    return db.fetch_one(
        """
        SELECT Users.name, Users.username FROM FatDays
        JOIN Users ON Users.telegram_id = FatDays.telegram_id
        WHERE FatDays.chat_id = ? AND FatDays.day = ?
        """,
        (chat_id, day),
    )


def claim(db, chat_id, day, user_id):
    """Returns False if the day already has a fatty, e.g. two /fat came in at once."""
    inserted_rows = db.execute(
        "INSERT OR IGNORE INTO FatDays (chat_id, day, telegram_id) VALUES (?, ?, ?)", (chat_id, day, user_id)
    )
    return inserted_rows == 1


def get_stats(db, chat_id, limit=10):
    return db.fetch_all(
        """
        SELECT Users.name, COUNT(*) AS days FROM FatDays
        JOIN Users ON Users.telegram_id = FatDays.telegram_id
        WHERE FatDays.chat_id = ?
        GROUP BY FatDays.telegram_id
        ORDER BY days DESC, MAX(FatDays.day) DESC
        LIMIT ?
        """,
        (chat_id, limit),
    )
