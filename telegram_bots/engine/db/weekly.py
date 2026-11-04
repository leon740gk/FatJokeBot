"""Numbers for the weekly summary: `since_day` is a Kyiv date "YYYY-MM-DD", timestamps go by the last 7 days."""

WEEK_AGO = "datetime('now', '-7 days')"


def count_message(db, chat_id, user_id, day):
    db.execute(
        """
        INSERT INTO MessageCounts (chat_id, telegram_id, day, count) VALUES (?, ?, ?, 1)
        ON CONFLICT (chat_id, telegram_id, day) DO UPDATE SET count = count + 1
        """,
        (chat_id, user_id, day),
    )


def messages(db, chat_id, since_day):
    """(name, messages) of everyone who wrote, the most talkative first."""
    return db.fetch_all(
        """
        SELECT Users.name, SUM(MessageCounts.count) AS total FROM MessageCounts
        JOIN Users ON Users.telegram_id = MessageCounts.telegram_id
        WHERE MessageCounts.chat_id = ? AND MessageCounts.day >= ?
        GROUP BY MessageCounts.telegram_id
        ORDER BY total DESC
        """,
        (chat_id, since_day),
    )


def silent(db, chat_id, since_day):
    """(name, username) of chat members who haven't written a word."""
    return db.fetch_all(
        """
        SELECT name, username FROM Users
        WHERE in_chat = 1 AND telegram_id NOT IN (
            SELECT telegram_id FROM MessageCounts WHERE chat_id = ? AND day >= ?
        )
        ORDER BY telegram_id
        """,
        (chat_id, since_day),
    )


def correct_answers(db):
    return db.fetch_all(
        f"""
        SELECT Users.name, COUNT(*) AS total FROM Answers
        JOIN Users ON Users.telegram_id = Answers.telegram_id
        WHERE Answers.is_correct = 1 AND Answers.answered_at >= {WEEK_AGO}
        GROUP BY Answers.telegram_id
        ORDER BY total DESC
        """
    )


def loot_points(db, chat_id):
    """(name, BP, Lords) of everyone who took loot."""
    return db.fetch_all(
        f"""
        SELECT Users.name, SUM(Loot.points) AS total, SUM(Loot.kind = 'lord') FROM Loot
        JOIN Users ON Users.telegram_id = Loot.taken_by
        WHERE Loot.chat_id = ? AND Loot.taken_at >= {WEEK_AGO}
        GROUP BY Loot.taken_by
        ORDER BY total DESC
        """,
        (chat_id,),
    )


def fat_days(db, chat_id, since_day):
    return db.fetch_all(
        """
        SELECT Users.name, COUNT(*) AS days FROM FatDays
        JOIN Users ON Users.telegram_id = FatDays.telegram_id
        WHERE FatDays.chat_id = ? AND FatDays.day >= ?
        GROUP BY FatDays.telegram_id
        ORDER BY days DESC
        """,
        (chat_id, since_day),
    )


def achievements(db):
    """(name, code) of the achievements unlocked this week, in the order they came."""
    return db.fetch_all(
        f"""
        SELECT Users.name, Achievements.code FROM Achievements
        JOIN Users ON Users.telegram_id = Achievements.telegram_id
        WHERE Achievements.unlocked_at >= {WEEK_AGO}
        ORDER BY Achievements.unlocked_at, Achievements.rowid
        """
    )


def gathered_parties(db, chat_id):
    return db.fetch_one(f"SELECT COUNT(*) FROM Parties WHERE chat_id = ? AND gathered_at >= {WEEK_AGO}", (chat_id,))[0]


def random_quote(db, chat_id):
    """(text, author_name, author_username, said_on) of a quote saved this week, or None."""
    return db.fetch_one(
        f"""
        SELECT text, author_name, author_username, said_on FROM Quotes
        WHERE chat_id = ? AND saved_at >= {WEEK_AGO}
        ORDER BY RANDOM() LIMIT 1
        """,
        (chat_id,),
    )
