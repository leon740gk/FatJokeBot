from datetime import datetime, timedelta

import pytest

from telegram_bots.bots.fat_joke.services import iq, texts
from telegram_bots.bots.fat_joke.services.reactions import Reply, StickerReplier, text_reactions
from telegram_bots.knowledge_base.fat_joke.reaction_data import (
    dick_short,
    sergios_rules,
    sternenko,
    sticker_responses,
)
from telegram_bots.tests.conftest import FakeRandom


def test_one_reply_per_keyword_group():
    # "сергій" and "серега" are in the same group, the old bot answered twice here
    assert text_reactions("Сергій, серега!", rng=FakeRandom()) == [Reply("text", sergios_rules[0])]


def test_text_triggers_several_kinds_of_replies():
    replies = text_reactions("який жах", rng=FakeRandom())
    assert Reply("text", "Я ж кажу, який жах...") in replies
    assert Reply("photo", sternenko) in replies


def test_philosophy_appears_by_chance():
    assert text_reactions("нічого цікавого", rng=FakeRandom(0.99)) == []
    assert len(text_reactions("нічого цікавого", rng=FakeRandom(0.0))) == 1


def test_special_sticker_always_answered():
    replier = StickerReplier(chance=0, rng=FakeRandom())
    assert replier.reply_for(1, dick_short) == Reply("text", "Опапа! Внєзапно!")


def test_ordinary_sticker_respects_chance_and_cooldown():
    now = datetime(2026, 10, 28, 12, 0)
    replier = StickerReplier(chance=0.5, cooldown=timedelta(minutes=5), rng=FakeRandom(0.1))
    assert replier.reply_for(1, "any", now=now) == Reply("text", sticker_responses[0])
    assert replier.reply_for(1, "any", now=now + timedelta(minutes=1)) is None
    assert replier.reply_for(2, "any", now=now + timedelta(minutes=1)) is not None
    assert replier.reply_for(1, "any", now=now + timedelta(minutes=6)) is not None
    assert StickerReplier(chance=0.5, rng=FakeRandom(0.9)).reply_for(1, "any", now=now) is None


@pytest.mark.parametrize(
    "iq_level, title",
    [(-5, "Пускає слину..."), (70, "Пускає слину..."), (71, "Мавпа з гранатою"), (171, "Кодзіма нервово курить...")],
)
def test_iq_levels(iq_level, title):
    assert iq.level_for(iq_level)[0] == title


def test_iq_table_sorted_with_prizes():
    table = iq.format_iq_table([("Low", 90), ("High", 150), ("Mid", 120), ("Last", 10)])
    assert table.index("🥇High") < table.index("🥈Mid") < table.index("🥉Low") < table.index("Last")


def test_change_message():
    assert iq.change_message(100, "Alex", increase=True)[0] == 101
    assert iq.change_message(100, "Alex", increase=False)[0] == 99


@pytest.mark.parametrize(
    "days, word",
    [(1, "день"), (2, "дні"), (4, "дні"), (5, "днів"), (11, "днів"), (14, "днів"), (21, "день"), (111, "днів")],
)
def test_days_word(days, word):
    assert texts.days_word(days) == word


def test_miss_you_message():
    assert texts.miss_you_message([]) is None
    assert "Alex @alex, про тебе ми не чули вже 3 дні" in texts.miss_you_message([("Alex", "alex", 3)])


def test_hour_message():
    assert texts.hour_message("13") == "Бам!!!\nЧас дня блеать! Можна на годинник не дивицця!"
