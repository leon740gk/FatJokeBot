"""Every bot speaks through the same engine, so its knowledge_base folder must have everything the engine reads."""

import importlib
import string

import pytest

from telegram_bots.config import load_settings
from telegram_bots.engine import content
from telegram_bots.engine.services import achievements, quiz

BOTS = sorted(path.name for path in content.KNOWLEDGE_BASE.iterdir() if (path / "texts.py").exists())


def names(bot, module):
    loaded = importlib.import_module(f"telegram_bots.knowledge_base.{bot}.{module}")
    return {name for name in vars(loaded) if not name.startswith("_")}


def placeholders(text):
    return {field for _, field, _, _ in string.Formatter().parse(text) if field}


@pytest.fixture
def activate():
    yield content.activate
    content.activate(content.DEFAULT_BOT)


def test_fat_joke_is_a_bot():
    assert "fat_joke" in BOTS


@pytest.mark.parametrize("bot", BOTS)
@pytest.mark.parametrize("module", content.MODULES)
def test_bot_has_what_fat_joke_has(bot, module):
    # FatJoke is the reference: the engine was written against it
    assert names("fat_joke", module) - names(bot, module) == set()


@pytest.mark.parametrize("bot", BOTS)
def test_texts_have_the_same_placeholders(bot):
    reference = importlib.import_module("telegram_bots.knowledge_base.fat_joke.texts")
    texts = importlib.import_module(f"telegram_bots.knowledge_base.{bot}.texts")
    for name, value in vars(reference).items():
        if isinstance(value, str):
            assert placeholders(getattr(texts, name)) == placeholders(value), name
        elif isinstance(value, tuple):
            assert len(getattr(texts, name)) == len(value), name


@pytest.mark.parametrize("bot", BOTS)
def test_theme_fits_the_engine(bot, activate):
    activate(bot)
    theme = content.kb.theme_data
    loot_codes = {kind[0] for kind in theme.loot_kinds}
    assert {theme.rare_loot, theme.top_loot} <= loot_codes
    assert set(theme.achievements) == set(achievements.CONDITIONS)
    assert quiz.disciplines() and theme.default_discipline in quiz.disciplines()


def test_kb_follows_the_active_bot(activate):
    assert content.kb.texts.__name__ == "telegram_bots.knowledge_base.fat_joke.texts"
    with pytest.raises(ValueError):
        activate("no_such_bot")
    assert content.active() == "fat_joke"


def test_settings_are_read_with_the_bot_prefix():
    environ = {
        "FAT_JOKE_BOT_TOKEN": "1:fat",
        "FAT_JOKE_QUIZ_DAILY_LIMIT": "5",
        "SERVO_SKULL_BOT_TOKEN": "2:skull",
        "SERVO_SKULL_WHO_POLL_ENABLED": "false",
    }
    fat_joke = load_settings("fat_joke", environ)
    servo_skull = load_settings("servo_skull", environ)
    assert (fat_joke.token, fat_joke.quiz_daily_limit, fat_joke.who_poll_enabled) == ("1:fat", 5, True)
    assert (servo_skull.token, servo_skull.quiz_daily_limit, servo_skull.who_poll_enabled) == ("2:skull", 20, False)
    # FatJoke keeps its old database and backups, the others get their own
    assert fat_joke.db_path.endswith("db_sqlite/my_database.db")
    assert servo_skull.db_path.endswith("db_sqlite/servo_skull.db")
    assert servo_skull.backup_dir.endswith("backups/servo_skull")
