def create(db, chat_id, message_id, user_id, comment):
    db.execute(
        "INSERT INTO Parties (chat_id, message_id, created_by, comment) VALUES (?, ?, ?, ?)",
        (chat_id, message_id, user_id, comment),
    )
    return db.fetch_one("SELECT id FROM Parties WHERE chat_id = ? AND message_id = ?", (chat_id, message_id))[0]


def get_open(db, chat_id, hours):
    """message_id of the party still gathering in this chat, started less than `hours` ago."""
    row = db.fetch_one(
        """
        SELECT message_id FROM Parties
        WHERE chat_id = ? AND gathered_at IS NULL AND created_at > datetime('now', ?)
        ORDER BY id DESC LIMIT 1
        """,
        (chat_id, f"-{hours} hours"),
    )
    return row[0] if row else None


def find(db, chat_id, message_id, hours):
    """(party_id, comment, is_gathered, is_expired) of the party on this message, or None."""
    return db.fetch_one(
        """
        SELECT id, comment, gathered_at IS NOT NULL, created_at <= datetime('now', ?) FROM Parties
        WHERE chat_id = ? AND message_id = ?
        """,
        (f"-{hours} hours", chat_id, message_id),
    )


def join(db, party_id, user_id, name, username):
    """Returns False if the user is already in the party."""
    inserted_rows = db.execute(
        "INSERT OR IGNORE INTO PartyMembers (party_id, telegram_id, name, username) VALUES (?, ?, ?, ?)",
        (party_id, user_id, name, username),
    )
    return inserted_rows == 1


def leave(db, party_id, user_id):
    """Returns False if the user wasn't in the party."""
    return db.execute("DELETE FROM PartyMembers WHERE party_id = ? AND telegram_id = ?", (party_id, user_id)) == 1


def members(db, party_id):
    """(telegram_id, name, username) in the order people joined."""
    return db.fetch_all(
        "SELECT telegram_id, name, username FROM PartyMembers WHERE party_id = ? ORDER BY rowid",
        (party_id,),
    )


def mark_gathered(db, party_id):
    """Returns False if the party was already gathered."""
    changed_rows = db.execute(
        "UPDATE Parties SET gathered_at = CURRENT_TIMESTAMP WHERE id = ? AND gathered_at IS NULL", (party_id,)
    )
    return changed_rows == 1
