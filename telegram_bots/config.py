import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _flag(value, default=False):
    value = (value or "").strip().lower()
    if not value:
        return default
    return value in ("1", "true", "yes", "on")


def env_prefix(bot):
    """fat_joke -> FAT_JOKE: every setting of the bot in .env starts with it, e.g. FAT_JOKE_BOT_TOKEN."""
    return bot.upper()


def _default_db_path(bot):
    # FatJoke keeps the file name it had before there were several bots
    name = "my_database.db" if bot == "fat_joke" else f"{bot}.db"
    return str(PROJECT_ROOT / "telegram_bots" / "db_sqlite" / name)


def _default_backup_dir(bot):
    return str(PROJECT_ROOT / "backups" if bot == "fat_joke" else PROJECT_ROOT / "backups" / bot)


@dataclass(frozen=True)
class Settings:
    bot: str  # the bot's folder in telegram_bots/knowledge_base, e.g. "fat_joke"
    token: str = ""
    main_chat_id: str = ""
    db_path: str = ":memory:"
    backup_dir: str = ""
    log_level: str = "INFO"
    # minutes to answer a quiz question before it closes
    quiz_answer_minutes: int = 15
    # quiz questions every 20 minutes; off while the chat is small, /quiz still works
    quiz_schedule_enabled: bool = False
    # how many /quiz questions one person can call a day (Kyiv time), 0 means no limit
    quiz_daily_limit: int = 20
    # Kyiv time hours without scheduled questions, "0-8" means from 00:00 to 07:59; empty turns quiet hours off
    quiz_quiet_hours: str = "0-8"
    # "we miss you" roll call of inactive members, was switched off in the old version
    miss_you_enabled: bool = False
    # a quote from the /save quote book in the main chat at 19:00 Kyiv time, skipped while the book is empty
    quote_of_the_day_enabled: bool = True
    # a "Кто из нас…" poll in the main chat every day at 12:00 Kyiv time; /who works anyway
    who_poll_enabled: bool = True
    # the weekly summary in the main chat on Sundays at 20:00 Kyiv time
    weekly_summary_enabled: bool = True

    @property
    def env_prefix(self):
        return env_prefix(self.bot)


def load_settings(bot, environ=None):
    """Settings of one bot from .env, all named <PREFIX>_..., see .env.example."""
    environ = os.environ if environ is None else environ
    prefix = env_prefix(bot)

    def get(name, default=""):
        return environ.get(f"{prefix}_{name}", default)

    return Settings(
        bot=bot,
        token=get("BOT_TOKEN"),
        main_chat_id=get("MAIN_CHAT_ID"),
        db_path=get("DB_PATH") or _default_db_path(bot),
        backup_dir=get("BACKUP_DIR") or _default_backup_dir(bot),
        log_level=get("LOG_LEVEL", "INFO").upper(),
        quiz_answer_minutes=int(get("QUIZ_ANSWER_MINUTES") or 15),
        quiz_schedule_enabled=_flag(get("QUIZ_SCHEDULE_ENABLED")),
        quiz_daily_limit=int(get("QUIZ_DAILY_LIMIT") or 20),
        quiz_quiet_hours=get("QUIZ_QUIET_HOURS", "0-8"),
        miss_you_enabled=_flag(get("MISS_YOU_ENABLED")),
        quote_of_the_day_enabled=_flag(get("QUOTE_OF_THE_DAY_ENABLED"), default=True),
        who_poll_enabled=_flag(get("WHO_POLL_ENABLED"), default=True),
        weekly_summary_enabled=_flag(get("WEEKLY_SUMMARY_ENABLED"), default=True),
    )


def require_token(settings):
    if not settings.token:
        raise RuntimeError(
            f"{settings.env_prefix}_BOT_TOKEN is not set, add it to {PROJECT_ROOT / '.env'} (see .env.example)"
        )
    return settings.token
