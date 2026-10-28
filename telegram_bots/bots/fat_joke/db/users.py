from datetime import datetime

DEFAULT_IQ = 100
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def register(db, user):
    """Adds a Telegram user to Users unless they are already there."""
    name = user.first_name or user.username or str(user.id)
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
    return db.fetch_all("SELECT name, username, activity_delta FROM Users WHERE activity_delta > 0")


def get_iq_and_name(db, user_id):
    return db.fetch_one("SELECT iq_level, name FROM Users WHERE telegram_id = ?", (user_id,))


def set_iq(db, user_id, iq_level):
    db.execute("UPDATE Users SET iq_level = ? WHERE telegram_id = ?", (iq_level, user_id))


def get_all_iq(db):
    return db.fetch_all("SELECT name, iq_level FROM Users")
