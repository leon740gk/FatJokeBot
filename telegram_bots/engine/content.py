"""Texts and data of the running bot, from telegram_bots/knowledge_base/<bot>/.

The engine is the same for every bot, each process runs one of them: main picks it with activate()
before anything is sent. The engine reads the content at call time through `kb`, never at import:
kb.texts.unknown_topic is telegram_bots/knowledge_base/<bot>/texts.py, unknown_topic.

Every bot's folder has the same modules: texts.py with every name FatJoke's has, the other modules with the names
in REQUIRED. telegram_bots/tests/test_content.py checks both.
"""

import importlib
from pathlib import Path

KNOWLEDGE_BASE = Path(__file__).resolve().parent.parent / "knowledge_base"
# the tests and anything started without a bot speak as FatJoke
DEFAULT_BOT = "fat_joke"
# what the engine reads from each module besides texts.py; the rest of a module is the bot's own business
REQUIRED = {
    "theme_data": (
        "points",
        "loot_kinds",
        "loot_button",
        "rare_loot",
        "top_loot",
        "late_phrases",
        "gone_line",
        "gone_phrase",
        "ranks",
        "achievements",
        "unlocked_phrases",
        "default_discipline",
    ),
    "reaction_data": (
        "text_to_text_reactions",
        "sticker_to_text_reactions",
        "photo_to_text_reactions",
        "animation_to_text_reactions",
        "special_sticker_responses",
        "sticker_responses",
        "commands_responses",
        "bot_commands",
        # stickers, animations and photos; None when the bot has none of its own
        "wanted",
        "quiz_correct_sticker",
        "quiz_wrong_sticker",
        "quiz_cheater_animation",
        "party_photo",
    ),
    "random_phrases": ("random_phrase_groups",),
    "timer_data": ("bam_title", "clocks"),
    "who_data": ("prefix", "who_questions"),
    "fat_day_data": ("scan_phrases", "winner_phrases", "already_phrases"),
    # the daily news, see engine/services/news.py; empty feeds turn them off
    "news_data": ("feeds", "sections", "per_section", "skip_words"),
}
MODULES = ("texts", *REQUIRED)

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
