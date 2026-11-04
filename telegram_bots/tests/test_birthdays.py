import asyncio
from datetime import date, datetime

from aiogram import methods
from aiogram.enums import MessageEntityType

from telegram_bots.engine.db import users as users_db
from telegram_bots.engine.scheduler import KYIV, birthday_greetings, create_scheduler
from telegram_bots.engine.services import birthdays
from telegram_bots.tests.conftest import FakeRandom
from telegram_bots.tests.fake_telegram import (
    CHAT,
    feed,
    reply_update,
    sent_texts,
    text_update,
    user,
)

TODAY = date(2026, 11, 4)


def test_parse():
    assert birthdays.parse("03.05", TODAY).stored() == "03.05"
    assert birthdays.parse("3/5/1990", TODAY).stored() == "03.05.1990"
    assert birthdays.parse(" 29-02-2000 ", TODAY).stored() == "29.02.2000"
    # 29.02 without a year is fine, with a non-leap year it isn't
    assert birthdays.parse("29.02", TODAY) and not birthdays.parse("29.02.2001", TODAY)
    for wrong in ("", "завтра", "32.01", "01.13", "03.05.1850", "03.05.2030", "05.12.2026", "1990-05-03"):
        assert birthdays.parse(wrong, TODAY) is None, wrong


def test_today_and_leap_day():
    rows = [
        (1, "Alex", "alex", "04.11.1990"),
        (2, "Bob", None, "04.11"),
        (3, "Leap", None, "29.02.2000"),
        (4, "Broken", None, "not a date"),
        (5, "Later", None, "05.11"),
    ]
    assert [row[0] for row in birthdays.todays(rows, TODAY)] == [1, 2]
    # in a year without February 29 the leap day birthday is on the 28th
    assert [row[0] for row in birthdays.todays(rows, date(2027, 2, 28))] == [3]
    assert [row[0] for row in birthdays.todays(rows, date(2028, 2, 29))] == [3]


def test_upcoming_list():
    rows = [(1, "Alex", "alex", "03.11.1990"), (2, "Bob", None, "04.11"), (3, "Cat", None, "10.11")]
    text = birthdays.format_upcoming(rows, TODAY)
    # nearest first; Alex's has just passed and goes to the end of the list
    assert text.index("Bob") < text.index("Cat") < text.index("Alex")
    assert "Bob — 04.11 (сегодня!)" in text and "Cat — 10.11 (через 6 дней)" in text
    assert "Alex — 03.11 (через 364 дня)" in text
    assert "Ни одного" in birthdays.format_upcoming([], TODAY)


def test_greeting_mentions_and_age():
    people = [(7, "Alex", "alex", birthdays.parse("04.11.1990", TODAY)), (8, "Bob", None, birthdays.parse("04.11"))]
    text, entities = birthdays.greeting(people, TODAY, FakeRandom()).render()
    assert "Alex — 36 лет!" in text and "Bob" in text and "Bob —" not in text
    assert [entity.user.id for entity in entities if entity.type == MessageEntityType.TEXT_MENTION] == [7, 8]


def test_birthday_command(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/birthday"))
    assert sent_texts(bot)[-1].startswith("🎂 Дня рождения пока не знаю.")

    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/birthday 31.02"))
    assert sent_texts(bot)[-1].startswith("Не похоже на дату")

    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/birthday 4.11.1990"))
    assert sent_texts(bot)[-1].startswith("🎂 Запомнил: Alex празднует 04.11.1990.")
    assert users_db.get_birthday(db, 7) == "04.11.1990"

    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/birthday"))
    assert sent_texts(bot)[-1].startswith("🎂 День рождения Alex: 04.11.1990")

    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/birthday -"))
    assert users_db.get_birthday(db, 7) is None


def test_admin_sets_someone_elses_birthday(db, bot, dispatcher):
    feed(dispatcher, bot, **reply_update(user(8, "Bob"), "/birthday 01.01", user(7, "Alex"), "hi"))
    assert sent_texts(bot)[-1].startswith("Указывать день рождения за других")
    assert users_db.get_birthday(db, 7) is None

    bot.session.admins.add(8)
    feed(dispatcher, bot, **reply_update(user(8, "Bob"), "/birthday 01.01", user(7, "Alex"), "hi"))
    assert users_db.get_birthday(db, 7) == "01.01" and users_db.get_birthday(db, 8) is None

    feed(dispatcher, bot, **text_update(user(8, "Bob"), "/birthdays"))
    assert "🎂 Alex — 01.01" in sent_texts(bot)[-1]


def test_morning_greeting(db, bot):
    today = datetime.now(KYIV).date()
    users_db.register(db, user(7, "Alex"))
    users_db.register(db, user(8, "Bob"))
    asyncio.run(birthday_greetings(bot, db, chat_id=CHAT.id))
    assert not bot.session.of_type(methods.SendMessage)

    users_db.set_birthday(db, 7, f"{today:%d.%m}")
    users_db.set_in_chat(db, 8, False)
    users_db.set_birthday(db, 8, f"{today:%d.%m}")
    asyncio.run(birthday_greetings(bot, db, chat_id=CHAT.id))
    sent = bot.session.of_type(methods.SendMessage)
    # Bob left the chat, only Alex is greeted
    assert len(sent) == 1 and [entity.user.id for entity in sent[0].entities if entity.user] == [7]


def test_greetings_are_scheduled(db, bot):
    def jobs(**flags):
        return {job.func.__name__ for job in create_scheduler(bot, db, CHAT.id, **flags).get_jobs()}

    assert "birthday_greetings" in jobs(birthdays_enabled=True)
    assert "birthday_greetings" not in jobs(birthdays_enabled=False)
