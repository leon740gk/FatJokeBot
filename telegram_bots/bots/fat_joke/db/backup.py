"""SQLite backups: once a day, plus on start if the last one is older than STARTUP_BACKUP_AGE.

The newest BACKUP_KEEP copies are kept.

Run by hand: python -m telegram_bots.bots.fat_joke.db.backup
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
BACKUP_KEEP = 14
STARTUP_BACKUP_AGE = timedelta(hours=20)
FILE_PREFIX = "fat_joke_"


def backup_database(db_path, backup_dir, keep=BACKUP_KEEP, now=None):
    """Copies the database with sqlite's online backup, safe while the bot is writing to it."""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"{FILE_PREFIX}{(now or datetime.now()).strftime('%Y-%m-%d_%H-%M-%S')}.db"

    source = sqlite3.connect(db_path)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    for old_backup in sorted(backup_dir.glob(f"{FILE_PREFIX}*.db"))[:-keep]:
        old_backup.unlink()
    logger.info("database backed up to %s", target)
    return target


def latest_backup(backup_dir):
    backups = sorted(Path(backup_dir).glob(f"{FILE_PREFIX}*.db"))
    return backups[-1] if backups else None


def backup_if_stale(db_path, backup_dir, max_age=STARTUP_BACKUP_AGE, now=None):
    """Backs up on start unless a fresh copy exists, so frequent restarts don't push out the daily copies."""
    now = now or datetime.now()
    latest = latest_backup(backup_dir)
    if latest and now - datetime.fromtimestamp(latest.stat().st_mtime) < max_age:
        return None
    return backup_database(db_path, backup_dir, now=now)


if __name__ == "__main__":
    from telegram_bots.config import BACKUP_DIR, DB_PATH

    logging.basicConfig(level=logging.INFO)
    backup_database(DB_PATH, BACKUP_DIR)
