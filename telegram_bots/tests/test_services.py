from datetime import datetime, timedelta
from random import Random

import pytest

from telegram_bots.bots.fat_joke.services import iq, texts
from telegram_bots.bots.fat_joke.services.reactions import Reply, StickerReplier, text_reactions
from telegram_bots.knowledge_base.fat_joke.random_phrases import random_phrase_groups
from telegram_bots.knowledge_base.fat_joke.reaction_data import (
    dick_short,
    sergios_rules,
    sternenko,
    sticker_responses,
)
from telegram_bots.knowledge_base.fat_joke.timer_data import hour_phrases
from telegram_bots.tests.conftest import FakeRandom


def test_one_reply_per_keyword_group():
    # "сергій" and "серега" are in the same group, the old bot answered twice here
    assert text_reactions("Сергій, серега!", rng=FakeRandom()) == [Reply("text", sergios_rules[0])]


def test_text_triggers_several_kinds_of_replies():
    replies = text_reactions("який жах", rng=FakeRandom())
    assert Reply("text", "Я ж говорю, какой ужас...") in replies
    assert Reply("photo", sternenko) in replies


def test_philosophy_appears_by_chance():
    assert text_reactions("нічого цікавого", rng=FakeRandom(0.99)) == []
    assert len(text_reactions("нічого цікавого", rng=FakeRandom(0.0))) == 1


def test_random_phrase_groups_are_picked_evenly(monkeypatch):
    # a group first, then a phrase in it, so 132 Podervianskyi quotes don't drown the facts
    monkeypatch.setattr("telegram_bots.bots.fat_joke.services.reactions.PHILOSOPHY_CHANCE", 1)
    assert all(random_phrase_groups) and len(random_phrase_groups) == 4
    picked = {text_reactions("тишина", rng=Random(seed))[-1].value for seed in range(200)}
    assert all(picked & set(group) for group in random_phrase_groups)


def test_special_sticker_always_answered():
    replier = StickerReplier(chance=0, rng=FakeRandom())
    assert replier.reply_for(1, dick_short) == Reply("text", "Опапа! Внезапно!")


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
    [(-5, "Пускает слюни..."), (70, "Пускает слюни..."), (71, "Обезьяна с гранатой"), (171, "Кодзима нервно курит...")],
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
    [(1, "день"), (2, "дня"), (4, "дня"), (5, "дней"), (11, "дней"), (14, "дней"), (21, "день"), (111, "дней")],
)
def test_days_word(days, word):
    assert texts.days_word(days) == word


def test_miss_you_message():
    assert texts.miss_you_message([]) is None
    assert "Alex @alex, о тебе мы не слышали уже 3 дня" in texts.miss_you_message([("Alex", "alex", 3)])


def test_hour_message():
    assert texts.hour_message("19", "18", rng=FakeRandom()) == (
        f"Бам!!! Говорит Омниссия!\n🇺🇦 19:00 - час {hour_phrases['ua']['evening'][0]}!\n"
        f"🇩🇪 18:00 - время {hour_phrases['de']['evening'][0]}!"
    )


def test_day_part_for_hours_around_midnight():
    assert [texts.day_part(hour) for hour in (0, 5, 6, 11, 12, 17, 18, 23)] == [
        "night",
        "night",
        "morning",
        "morning",
        "day",
        "day",
        "evening",
        "evening",
    ]
