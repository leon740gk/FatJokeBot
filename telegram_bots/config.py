import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _required(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set, add it to {PROJECT_ROOT / '.env'} (see .env.example)")
    return value


def _flag(name, default=False):
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in ("1", "true", "yes", "on")


def get_bot_token():
    return _required("FAT_JOKE_BOT_TOKEN")


MAIN_CHAT_ID = os.getenv("FAT_JOKE_MAIN_CHAT_ID", "")
DB_PATH = os.getenv("FAT_JOKE_DB_PATH") or str(PROJECT_ROOT / "telegram_bots" / "db_sqlite" / "my_database.db")
BACKUP_DIR = os.getenv("FAT_JOKE_BACKUP_DIR") or str(PROJECT_ROOT / "backups")
LOG_LEVEL = os.getenv("FAT_JOKE_LOG_LEVEL", "INFO").upper()
# minutes to answer a quiz question before it closes
QUIZ_ANSWER_MINUTES = int(os.getenv("FAT_JOKE_QUIZ_ANSWER_MINUTES") or 15)
# quiz questions every 20 minutes; off while the chat is small, /quiz still works
QUIZ_SCHEDULE_ENABLED = _flag("FAT_JOKE_QUIZ_SCHEDULE_ENABLED")
# Kyiv time hours without scheduled questions, "0-8" means from 00:00 to 07:59; empty turns quiet hours off
QUIZ_QUIET_HOURS = os.getenv("FAT_JOKE_QUIZ_QUIET_HOURS", "0-8")
# "we miss you" roll call of inactive members, was switched off in the old version
MISS_YOU_ENABLED = _flag("FAT_JOKE_MISS_YOU_ENABLED")
# a quote from the /save quote book in the main chat at 19:00 Kyiv time, skipped while the book is empty
QUOTE_OF_THE_DAY_ENABLED = _flag("FAT_JOKE_QUOTE_OF_THE_DAY_ENABLED", default=True)
