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


def _parse_user_ids(raw):
    # "me=123,valodya=456" -> {"me": 123, "valodya": 456}
    user_ids = {}
    for pair in filter(None, (item.strip() for item in raw.split(","))):
        name, user_id = pair.split("=")
        user_ids[name.strip()] = int(user_id)
    return user_ids


def get_bot_token():
    return _required("FAT_JOKE_BOT_TOKEN")


MAIN_CHAT_ID = os.getenv("FAT_JOKE_MAIN_CHAT_ID", "")
TEST_CHAT_ID = os.getenv("FAT_JOKE_TEST_CHAT_ID", "")
USER_IDS = _parse_user_ids(os.getenv("FAT_JOKE_USER_IDS", ""))
DB_PATH = os.getenv("FAT_JOKE_DB_PATH") or str(PROJECT_ROOT / "telegram_bots" / "db_sqlite" / "my_database.db")
