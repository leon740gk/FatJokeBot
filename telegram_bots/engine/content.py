"""Texts and data of the running bot, from telegram_bots/knowledge_base/<bot>/.

The engine is the same for every bot, each process runs one of them: main picks it with activate()
before anything is sent. The engine reads the content at call time through `kb`, never at import:
kb.texts.unknown_topic is telegram_bots/knowledge_base/<bot>/texts.py, unknown_topic.

Every bot's folder has the same modules with the same names, telegram_bots/tests/test_content.py checks it.
"""

import importlib
from pathlib import Path

KNOWLEDGE_BASE = Path(__file__).resolve().parent.parent / "knowledge_base"
# the tests and anything started without a bot speak as FatJoke
DEFAULT_BOT = "fat_joke"
MODULES = ("texts", "theme_data", "reaction_data", "random_phrases", "timer_data", "who_data", "fat_day_data")

_active = DEFAULT_BOT


def activate(bot):
    global _active
    if not (KNOWLEDGE_BASE / bot).is_dir():
        raise ValueError(f"no bot {bot!r}: {KNOWLEDGE_BASE / bot} doesn't exist")
    _active = bot


def active():
    return _active


def quiz_dir():
    return KNOWLEDGE_BASE / _active / "quiz"


class _KnowledgeBase:
    def __getattr__(self, module):
        if module not in MODULES:
            raise AttributeError(module)
        return importlib.import_module(f"telegram_bots.knowledge_base.{_active}.{module}")


kb = _KnowledgeBase()
