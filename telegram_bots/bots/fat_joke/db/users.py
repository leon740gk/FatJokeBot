from datetime import datetime

from telegram_bots.bots.fat_joke.services.people import display_name

DEFAULT_IQ = 100
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def register(db, user):
    """Adds a Telegram user to Users unless they are already there."""
    name = display_name(user)
    db.execute(
        """
        INSERT INTO Users (telegram_id, name, username, iq_level, questionare_done)
        SELECT ?, ?, ?, ?, '[]'
        WHERE NOT EXISTS (SELECT 1 FROM Users WHERE telegram_id = ?)
        """,
        (user.id, name, user.username, DEFAULT_IQ, user.id),
    )


def touch_activity(db, user_id, now=None):
    now = (now or datetime.now()).strftime(DATE_FORMAT)
    db.execute("UPDATE Users SET last_message_date = ? WHERE telegram_id = ?", (now, user_id))


def update_activity_deltas(db, now=None):
    """Stores how many days ago each user wrote their last message."""
    now = now or datetime.now()
    for user_id, last_message_date in db.fetch_all("SELECT telegram_id, last_message_date FROM Users"):
        delta_days = 0
        if last_message_date:
            delta_days = (now - datetime.strptime(last_message_date, DATE_FORMAT)).days
        db.execute("UPDATE Users SET activity_delta = ? WHERE telegram_id = ?", (delta_days, user_id))


def get_inactive(db):
    return db.fetch_all("SELECT name, username, activity_delta FROM Users WHERE activity_delta > 0 AND in_chat = 1")


def get_iq_and_name(db, user_id):
    return db.fetch_one("SELECT iq_level, name FROM Users WHERE telegram_id = ?", (user_id,))


def set_iq(db, user_id, iq_level):
    db.execute("UPDATE Users SET iq_level = ? WHERE telegram_id = ?", (iq_level, user_id))


def get_all_iq(db):
    return db.fetch_all("SELECT name, iq_level FROM Users WHERE in_chat = 1")


def get_active_since(db, since):
    """(telegram_id, name, username) of everyone who wrote after `since`."""
    return db.fetch_all(
        """
        SELECT telegram_id, name, username FROM Users
        WHERE last_message_date >= ? AND in_chat = 1
        ORDER BY telegram_id
        """,
        (since.strftime(DATE_FORMAT),),
    )


def set_in_chat(db, user_id, in_chat):
    db.execute("UPDATE Users SET in_chat = ? WHERE telegram_id = ?", (int(in_chat), user_id))


def update_profile(db, user):
    """Refreshes the name and username, people change them over time."""
    db.execute(
        "UPDATE Users SET name = ?, username = ? WHERE telegram_id = ?", (display_name(user), user.username, user.id)
    )


def get_profile(db, user_id):
    """(telegram_id, name, username) of the user."""
    return db.fetch_one("SELECT telegram_id, name, username FROM Users WHERE telegram_id = ?", (user_id,))


def get_all_ids(db):
    return [row[0] for row in db.fetch_all("SELECT telegram_id FROM Users ORDER BY telegram_id")]
