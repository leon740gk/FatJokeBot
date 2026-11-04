"""ServoSkull runs on the same engine as FatJoke: a few rounds through the dispatcher in its Ukrainian texts."""

import asyncio

import pytest
from aiogram import methods

from telegram_bots.engine import content
from telegram_bots.engine.scheduler import hourly_bam, weekly_summary
from telegram_bots.engine.services import quiz
from telegram_bots.tests.fake_telegram import (
    CHAT,
    LootRandom,
    feed,
    press,
    press_loot,
    sent_question,
    sent_texts,
    text_update,
    user,
)


@pytest.fixture(autouse=True)
def servo_skull():
    content.activate("servo_skull")
    yield
    content.activate(content.DEFAULT_BOT)


def test_help_and_quiz_speak_ukrainian(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/help"))
    assert "Що вміє" not in sent_texts(bot)[-1] and "/quiz - питання вікторини" in sent_texts(bot)[-1]

    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz"))
    assert sent_texts(bot)[-1] == "Яку тему хочете? 👇"
    # only the topics of ServoSkull's own quiz folder: no MLBB, a gaming topic instead
    assert set(quiz.disciplines()) == {"ukr", "geo", "bio", "mix", "accounting", "welding", "games"}
    assert {len(topic.questions) for topic in quiz.disciplines().values()} == {150}
    assert quiz.current_discipline(db) == "games"

    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz мова"))
    question_id = bot.session.next_message_id
    message, buttons = sent_question(bot)
    assert message.text.startswith("Українська мова.")
    number = db.fetch_one("SELECT question_number FROM QuizMessages WHERE message_id = ?", (question_id,))[0]
    correct = quiz.get_question("ukr", number).correct
    right = next(b for b in buttons if quiz.parse_callback(b.callback_data).option_index in correct)
    feed(dispatcher, bot, **press(user(7, "Alex"), question_id, right.callback_data))
    edited = bot.session.of_type(methods.EditMessageText)[-1].text
    assert "Твій рівень IQ виріс з 100 до 101!" in edited
    # no stickers of its own yet: nothing is sent instead of FatJoke's
    assert not bot.session.of_type(methods.SendSticker)


def test_bam_is_kyiv_only_with_gaming_drop(db, bot, dispatcher):
    asyncio.run(hourly_bam(bot, db, chat_id=CHAT.id, rng=LootRandom("legendary")))
    sent = bot.session.of_type(methods.SendMessage)[-1]
    assert sent.text.startswith("Бам!!! Серво-череп на зв'язку!\n🇺🇦 ")
    assert "🇩🇪" not in sent.text and "ЛЕГЕНДАРНИЙ ДРОП" in sent.text and "+25 XP" in sent.text

    press_loot(dispatcher, bot, user(7, "Alex"), bot.session.next_message_id, sent.text)
    assert "Легендарний дроп забрав(ла) Alex (@alex)" in bot.session.of_type(methods.EditMessageText)[-1].text

    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/me"))
    profile = sent_texts(bot)[-1]
    assert "🏅 Ранг:" in profile and "XP" in profile and "з них легендарного: 1" in profile


def test_weekly_summary_and_reactions(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "знову лаги, я так не можу"))
    assert (
        sent_texts(bot)[-1]
        in content.kb.reaction_data.text_to_text_reactions[("лагає", "лаги", "лаганув", "високий пінг", "пінг під")]
    )
    # "багато" must not wake the bug joke
    count = len(sent_texts(bot))
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "багато роботи сьогодні"))
    assert len(sent_texts(bot)) == count

    asyncio.run(weekly_summary(bot, db, chat_id=CHAT.id))
    assert sent_texts(bot)[-1].startswith("📅 Підсумки тижня")
