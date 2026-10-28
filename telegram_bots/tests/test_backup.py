import os
import sqlite3
from datetime import datetime, timedelta

from telegram_bots.bots.fat_joke.db.backup import backup_database, backup_if_stale


def make_db(path):
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE Users (name TEXT)")
    connection.execute("INSERT INTO Users VALUES ('Alex')")
    connection.commit()
    return connection


def test_backup_is_a_working_copy(tmp_path):
    make_db(tmp_path / "bot.db").close()
    target = backup_database(tmp_path / "bot.db", tmp_path / "backups", now=datetime(2026, 10, 28, 4, 0))
    assert target.name == "fat_joke_2026-10-28_04-00-00.db"
    assert sqlite3.connect(target).execute("SELECT name FROM Users").fetchall() == [("Alex",)]


def test_backup_works_while_the_bot_holds_the_database_open(tmp_path):
    connection = make_db(tmp_path / "bot.db")
    connection.execute("INSERT INTO Users VALUES ('Bob')")
    connection.commit()
    target = backup_database(tmp_path / "bot.db", tmp_path / "backups")
    assert len(sqlite3.connect(target).execute("SELECT name FROM Users").fetchall()) == 2
    connection.close()


def test_only_newest_copies_are_kept(tmp_path):
    make_db(tmp_path / "bot.db").close()
    start = datetime(2026, 10, 1)
    for day in range(5):
        backup_database(tmp_path / "bot.db", tmp_path / "backups", keep=3, now=start + timedelta(days=day))
    names = sorted(path.name for path in (tmp_path / "backups").iterdir())
    assert names == [f"fat_joke_2026-10-0{day}_00-00-00.db" for day in (3, 4, 5)]


def test_startup_backup_skipped_when_a_fresh_copy_exists(tmp_path):
    make_db(tmp_path / "bot.db").close()
    now = datetime(2026, 10, 28, 12, 0)
    first = backup_if_stale(tmp_path / "bot.db", tmp_path / "backups", now=now)
    os.utime(first, (now.timestamp(), now.timestamp()))
    assert backup_if_stale(tmp_path / "bot.db", tmp_path / "backups", now=now + timedelta(hours=2)) is None
    assert backup_if_stale(tmp_path / "bot.db", tmp_path / "backups", now=now + timedelta(hours=21)) is not None
