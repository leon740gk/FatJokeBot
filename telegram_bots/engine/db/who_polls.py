import json


def create(db, chat_id, message_id, question, options):
    """options are (telegram_id, name, username) in the order of the poll."""
    db.execute(
        "INSERT INTO WhoPolls (chat_id, message_id, question, options) VALUES (?, ?, ?, ?)",
        (chat_id, message_id, question, json.dumps(options, ensure_ascii=False)),
    )


def get_open(db, chat_id):
    """message_id of the poll still running in the chat, or None."""
    row = db.fetch_one("SELECT message_id FROM WhoPolls WHERE chat_id = ? AND closed_at IS NULL", (chat_id,))
    return row[0] if row else None


def used_questions(db, chat_id):
    return {row[0] for row in db.fetch_all("SELECT question FROM WhoPolls WHERE chat_id = ?", (chat_id,))}


def take_expired(db, hours):
    """Closes polls older than `hours` and returns (chat_id, message_id, question, options) of each."""
    rows = db.fetch_all(
        """
        SELECT id, chat_id, message_id, question, options FROM WhoPolls
        WHERE closed_at IS NULL AND created_at <= datetime('now', ?)
        """,
        (f"-{hours} hours",),
    )
    for row in rows:
        db.execute("UPDATE WhoPolls SET closed_at = CURRENT_TIMESTAMP WHERE id = ?", (row[0],))
    return [
        (chat_id, message_id, question, [tuple(option) for option in json.loads(options)])
        for _, chat_id, message_id, question, options in rows
    ]
