"""Chat games of ServoSkull: polls, the question of the day, riddles, reactions and anonymous messages."""

import asyncio
import time
from datetime import datetime

import pytest
from aiogram import methods
from aiogram.types import Chat, Message

from telegram_bots.config import Settings
from telegram_bots.engine import content, main
from telegram_bots.engine.db import chat_games as games_db
from telegram_bots.engine.scheduler import create_scheduler, daily_question, riddle_tick, start_this_or_that
from telegram_bots.engine.services import achievements, chat_games
from telegram_bots.tests.fake_telegram import BOT_USER, CHAT, feed, reply_update, sent_texts, text_update, user

ALEX = user(7, "Alex")
BOB = user(8, "Bob")


@pytest.fixture(autouse=True)
def servo_skull():
    content.activate("servo_skull")
    yield
    content.activate(content.DEFAULT_BOT)


def riddle_of(db):
    current = games_db.open_riddle(db, CHAT.id)
    return current, chat_games.get_riddle(current[2])


def test_answers_are_matched_loosely():
    riddle = chat_games.Riddle("🐺", ("",), ("The Witcher 3", "відьмак"))
    assert chat_games.is_answer("це ж THE witcher 3!!!", riddle)
    assert chat_games.is_answer("Відьмак", riddle)
    assert not chat_games.is_answer("the witcher", riddle)
    assert chat_games.is_answer("Baldurs gate?", chat_games.Riddle("🎲", (), ("Baldur's Gate 3", "baldurs gate")))


def test_content_fits_telegram():
    data = content.kb.chat_games_data
    assert 2 <= len(data.tonight_options) <= 10
    assert all(len(option) <= 100 for _, *options in data.this_or_that for option in options)
    # questions and pairs go round without repeats, a duplicate would come twice as often
    assert len(set(data.this_or_that)) == len(data.this_or_that)
    assert len(set(data.daily_questions)) == len(data.daily_questions)
    for riddle in chat_games.riddles():
        assert riddle.hints and riddle.answers
        assert all(len(chat_games.normalize(answer)) >= 2 for answer in riddle.answers), riddle.answers
        # no riddle is solved by its own hints
        assert not any(chat_games.is_answer(hint, riddle) for hint in riddle.hints), riddle.answers


def test_riddle_round(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(ALEX, "/guess"))
    riddle_message = bot.session.next_message_id
    assert sent_texts(bot)[-1].startswith("🎮 Вгадай гру!") and "15 XP" in sent_texts(bot)[-1]
    current, riddle = riddle_of(db)

    feed(dispatcher, bot, **text_update(BOB, "/guess"))
    assert sent_texts(bot)[-1] == "Загадка вже висить, відгадуй 👆"
    assert bot.session.of_type(methods.SendMessage)[-1].reply_parameters.message_id == riddle_message

    count = len(sent_texts(bot))
    feed(dispatcher, bot, **text_update(BOB, "хм, не знаю"))
    assert len(sent_texts(bot)) == count and games_db.open_riddle(db, CHAT.id)

    feed(dispatcher, bot, **text_update(BOB, f"це {riddle.answers[-1].upper()}?"))
    assert sent_texts(bot)[-1].startswith(f"🎉 Bob (@bob) вгадав(ла)! Це {riddle.answers[0]}. +15 XP")
    assert not games_db.open_riddle(db, CHAT.id)
    assert achievements.battle_points(db, BOB.id) == 15

    # a late right answer gives nothing
    feed(dispatcher, bot, **text_update(ALEX, riddle.answers[0]))
    assert achievements.battle_points(db, ALEX.id) == 0


def test_riddle_hints_and_answer(db, bot):
    start = time.time()
    games_db.create_riddle(db, CHAT.id, 500, 0, started_at=start)
    riddle = chat_games.get_riddle(0)
    minute = 60

    asyncio.run(riddle_tick(bot, db, now=start + 29 * minute))
    assert not sent_texts(bot)
    asyncio.run(riddle_tick(bot, db, now=start + 30 * minute))
    assert sent_texts(bot) == [f"💡 Підказка 1: {riddle.hints[0]}\nТепер за відповідь 10 XP"]
    asyncio.run(riddle_tick(bot, db, now=start + 31 * minute))
    assert len(sent_texts(bot)) == 1
    asyncio.run(riddle_tick(bot, db, now=start + 60 * minute))
    assert sent_texts(bot)[-1].startswith("💡 Підказка 2:") and "5 XP" in sent_texts(bot)[-1]
    asyncio.run(riddle_tick(bot, db, now=start + 90 * minute))
    assert sent_texts(bot)[-1] == f"⌛ Ніхто не вгадав. Відповідь: {riddle.answers[0]}"
    assert bot.session.of_type(methods.SendMessage)[-1].reply_parameters.message_id == 500
    assert not games_db.open_riddle(db, CHAT.id)
    assert chat_games.riddle_points(2) == 5


def test_daily_question_answers(db, bot, dispatcher):
    asyncio.run(daily_question(bot, db, chat_id=CHAT.id))
    question_id = bot.session.next_message_id
    text = sent_texts(bot)[-1]
    assert text.startswith("❓ Питання дня:") and "+3 XP" in text

    for _ in range(2):
        feed(
            dispatcher,
            bot,
            **reply_update(ALEX, "Тетріс на тетрісі", BOT_USER, text, message_id=900, original_id=question_id),
        )
    reactions = bot.session.of_type(methods.SetMessageReaction)
    assert len(reactions) == 1 and reactions[0].reaction[0].emoji == "✍"
    assert achievements.battle_points(db, ALEX.id) == 3

    # a reply to some other message of the bot is not an answer
    feed(dispatcher, bot, **reply_update(BOB, "ага", BOT_USER, "Бам!!!", message_id=901, original_id=1))
    assert achievements.battle_points(db, BOB.id) == 0


def test_polls(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(ALEX, "/vs"))
    poll = bot.session.of_type(methods.SendPoll)[-1]
    assert poll.is_anonymous and len(poll.options) == 2

    feed(dispatcher, bot, **text_update(ALEX, "/tonight"))
    poll = bot.session.of_type(methods.SendPoll)[-1]
    assert poll.question == "🎮 Сьогодні ввечері граю в…"
    assert not poll.is_anonymous and poll.allows_multiple_answers
    assert poll.options[-1] == "Сьогодні відпочиваю 😴"

    # every "Це чи те" comes once before any comes again
    total = len(content.kb.chat_games_data.this_or_that)
    for _ in range(total - 1):
        asyncio.run(start_this_or_that(bot, db, CHAT.id))
    assert games_db.used_this_or_that(db, CHAT.id) == set(range(total))


def test_games_in_private_chat(db, bot, dispatcher):
    private = Chat(id=7, type="private")
    message = Message(message_id=1, date=datetime.now(), chat=private, from_user=ALEX, text="/guess")
    feed(dispatcher, bot, message=message)
    assert sent_texts(bot) == ["Ця команда працює лише в групі 👥"]


def test_reactions_from_the_bot(db, bot, dispatcher, monkeypatch):
    monkeypatch.setattr(chat_games, "REACTION_CHANCE", 1)
    feed(dispatcher, bot, **text_update(ALEX, "всім привіт"))
    feed(dispatcher, bot, **text_update(ALEX, "як справи"))
    reactions = bot.session.of_type(methods.SetMessageReaction)
    # once per cooldown in a chat
    assert len(reactions) == 1
    assert reactions[0].reaction[0].emoji in content.kb.reaction_data.message_reactions


def test_fat_joke_has_no_games_yet(db, bot, dispatcher, monkeypatch):
    content.activate("fat_joke")
    monkeypatch.setattr(chat_games, "REACTION_CHANCE", 1)
    feed(dispatcher, bot, **text_update(ALEX, "/guess"))
    feed(dispatcher, bot, **text_update(ALEX, "/vs"))
    assert sent_texts(bot) == ["Такого у этого бота пока нет 🤷"] * 2
    assert not bot.session.of_type(methods.SetMessageReaction)

    games = {"daily_question", "this_or_that_poll", "scheduled_riddle", "tonight_poll"}
    flags = dict.fromkeys(
        ("daily_question_enabled", "this_or_that_enabled", "riddles_enabled", "tonight_poll_enabled"), True
    )
    jobs = {job.func.__name__ for job in create_scheduler(bot, db, CHAT.id, **flags).get_jobs()}
    assert not games & jobs
    content.activate("servo_skull")
    jobs = {job.func.__name__ for job in create_scheduler(bot, db, CHAT.id, **flags).get_jobs()}
    assert games <= jobs


@pytest.fixture
def anon_dispatcher(db):
    settings = Settings(bot="servo_skull", main_chat_id=str(CHAT.id), anon_enabled=True)
    yield main.build_dispatcher(db, settings)
    for router in main.ROUTERS:
        router._parent_router = None


def private_message(from_user, text):
    chat = Chat(id=from_user.id, type="private")
    return Message(message_id=1, date=datetime.now(), chat=chat, from_user=from_user, text=text)


def test_anonymous_messages(db, bot, anon_dispatcher):
    feed(anon_dispatcher, bot, message=private_message(ALEX, "/anon"))
    assert sent_texts(bot)[-1].startswith("🕵️ Напиши мені в особисті /anon")

    feed(anon_dispatcher, bot, message=private_message(ALEX, "/anon хто сьогодні в доту?"))
    posted, answer = bot.session.of_type(methods.SendMessage)[-2:]
    assert posted.chat_id == str(CHAT.id) and posted.text == "🕵️ Анонімно:\n\nхто сьогодні в доту?"
    assert answer.chat_id == ALEX.id and answer.text.startswith("Надіслано 🤫")
    # the text itself is not kept
    assert db.fetch_all("SELECT telegram_id FROM AnonMessages") == [(ALEX.id,)]

    for _ in range(chat_games.ANON_DAILY_LIMIT):
        feed(anon_dispatcher, bot, message=private_message(ALEX, "/anon ще"))
    assert sent_texts(bot)[-1] == "На сьогодні досить: не більше 3 анонімок на день 🤐"
    assert games_db.anon_sent_on(db, ALEX.id, datetime.now().date().isoformat()) <= chat_games.ANON_DAILY_LIMIT

    bot.session.left_users.add(BOB.id)
    feed(anon_dispatcher, bot, message=private_message(BOB, "/anon привіт"))
    assert sent_texts(bot)[-1] == "Анонімки можуть писати лише учасники чату 🤷"


def test_anon_in_the_group_is_taken_away(db, bot, anon_dispatcher):
    feed(anon_dispatcher, bot, **text_update(ALEX, "/anon секрет"))
    assert bot.session.of_type(methods.DeleteMessage)
    assert sent_texts(bot) == ["🤫 Анонімки пишуть мені в особисті: https://t.me/fat_joke_bot"]


def test_anon_is_off_by_default(db, bot, dispatcher):
    feed(dispatcher, bot, message=private_message(ALEX, "/anon привіт"))
    assert sent_texts(bot) == ["Анонімки в цього бота вимкнені 🤐"]


def test_start_in_private_tells_about_anon(db, bot, anon_dispatcher):
    feed(anon_dispatcher, bot, message=private_message(ALEX, "/start"))
    assert sent_texts(bot)[-1].startswith("🕵️ Напиши мені в особисті")
