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


def _flag(name):
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def get_bot_token():
    return _required("FAT_JOKE_BOT_TOKEN")


MAIN_CHAT_ID = os.getenv("FAT_JOKE_MAIN_CHAT_ID", "")
DB_PATH = os.getenv("FAT_JOKE_DB_PATH") or str(PROJECT_ROOT / "telegram_bots" / "db_sqlite" / "my_database.db")
LOG_LEVEL = os.getenv("FAT_JOKE_LOG_LEVEL", "INFO").upper()
# "we miss you" roll call of inactive members, was switched off in the old version
MISS_YOU_ENABLED = _flag("FAT_JOKE_MISS_YOU_ENABLED")
