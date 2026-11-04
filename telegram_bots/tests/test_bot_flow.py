"""Feeds real Telegram updates through the aiogram dispatcher, with a fake session instead of the network."""

import asyncio
from datetime import datetime

import pytest
from aiogram import Bot, methods
from aiogram.types import (
    ChatMemberLeft,
    ChatMemberMember,
    ChatMemberUpdated,
    Message,
)

from telegram_bots.config import Settings
from telegram_bots.engine import main
from telegram_bots.engine import scheduler as scheduler_module
from telegram_bots.engine.db import quiz as quiz_db
from telegram_bots.engine.db import users as users_db
from telegram_bots.engine.db.duels import COLUMNS as DUEL_COLUMNS
from telegram_bots.engine.handlers import fat_day as fat_day_handlers
from telegram_bots.engine.handlers import reactions
from telegram_bots.engine.scheduler import (
    KYIV,
    ask_question,
    check_chat,
    close_duels,
    close_expired_questions,
    close_who_polls,
    create_scheduler,
    hourly_bam,
    quote_of_the_day,
    scheduled_question,
    weekly_summary,
    who_poll,
)
from telegram_bots.engine.services import achievements, bets, duel, loot, party, quiz
from telegram_bots.knowledge_base.fat_joke import reaction_data
from telegram_bots.knowledge_base.fat_joke.reaction_data import bot_commands, red_blink
from telegram_bots.knowledge_base.fat_joke.theme_data import gone_phrase, late_phrases
from telegram_bots.tests.fake_telegram import (
    BOT_USER,
    CHAT,
    FakeSession,
    LootRandom,
    feed,
    press,
    press_loot,
    reply_update,
    sent_question,
    sent_texts,
    text_update,
    user,
)


def test_help_command_replies_and_registers_user(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Newbie"), "/help@fat_joke_bot"))
    sent = bot.session.of_type(methods.SendMessage)
    assert len(sent) == 1 and "/show_iq" in sent[0].text
    assert users_db.get_iq_and_name(db, 7) == (100, "Newbie")


def test_text_keywords_reply_once_per_group(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Newbie"), "Сергій, серега, хайль"))
    texts = [request.text for request in bot.session.of_type(methods.SendMessage)]
    assert len(texts) == 1 and texts[0].startswith("10 правил Серджио")
    assert len(bot.session.of_type(methods.SendSticker)) == 1


def test_quiz_round(db, bot, dispatcher):
    users_db.register(db, user(7, "Alex"))
    users_db.register(db, user(8, "Bob"))
    asyncio.run(ask_question(bot, db, CHAT.id))
    question_message, buttons = sent_question(bot)
    assert question_message.text.startswith("MLBB 2.") and len(buttons) == 4

    parsed = quiz.parse_callback(buttons[0].callback_data)
    is_correct = parsed.option_index in quiz.get_question(parsed.discipline, parsed.number).correct
    message_id = bot.session.next_message_id

    feed(dispatcher, bot, **press(user(7, "Alex"), message_id, buttons[0].callback_data))
    edited = bot.session.of_type(methods.EditMessageText)[-1].text
    assert "Правильный ответ:" in edited
    assert users_db.get_iq_and_name(db, 7)[0] == (101 if is_correct else 99)

    # Bob presses a button on the same message a moment later: nothing is counted
    feed(dispatcher, bot, **press(user(8, "Bob"), message_id, buttons[1].callback_data))
    assert bot.session.of_type(methods.AnswerCallbackQuery)[-1].text == "Этот вопрос уже закрыт"
    assert users_db.get_iq_and_name(db, 8)[0] == 100

    # the same question asked again in the same season: Alex is caught cheating
    quiz_db.save_quiz_message(db, CHAT.id, 5000, parsed.discipline, 1, parsed.number)
    feed(dispatcher, bot, **press(user(7, "Alex"), 5000, buttons[1].callback_data))
    assert bot.session.of_type(methods.SendAnimation)[-1].animation == red_blink
    assert "Читер в чате" in bot.session.of_type(methods.EditMessageText)[-1].text


def test_one_own_question_at_a_time(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz мобла"))
    alex_question = bot.session.next_message_id
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz бух"))
    # someone else's open question doesn't stop Bob, even on the same topic
    feed(dispatcher, bot, **text_update(user(8, "Bob"), "/quiz по мобле"))
    sent = bot.session.of_type(methods.SendMessage)
    assert sent[0].text.startswith("MLBB 2.")
    assert sent[1].text == "Сначала ответь на свой вопрос 👆" and sent[1].reply_parameters.message_id == alex_question
    assert sent[2].text.startswith("MLBB 2.")
    assert db.fetch_all("SELECT asked_by, discipline FROM QuizMessages ORDER BY id") == [(7, "mlbb2"), (8, "mlbb2")]


def test_only_the_caller_can_answer(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz мобла"))
    message_id = bot.session.next_message_id
    _, buttons = sent_question(bot)

    feed(dispatcher, bot, **press(user(8, "Bob"), message_id, buttons[0].callback_data))
    alert = bot.session.of_type(methods.AnswerCallbackQuery)[-1]
    assert alert.show_alert and alert.text.startswith("Ворюга! 😈 Это вопрос для Alex")
    assert not bot.session.of_type(methods.EditMessageText) and users_db.get_iq_and_name(db, 8)[0] == 100
    assert db.fetch_one("SELECT COUNT(*) FROM Answers")[0] == 0

    feed(dispatcher, bot, **press(user(7, "Alex"), message_id, buttons[0].callback_data))
    assert bot.session.of_type(methods.EditMessageText)[-1].message_id == message_id
    assert db.fetch_all("SELECT telegram_id FROM Answers") == [(7,)]
    # after the answer it's simply closed for everyone
    feed(dispatcher, bot, **press(user(8, "Bob"), message_id, buttons[1].callback_data))
    assert bot.session.of_type(methods.AnswerCallbackQuery)[-1].text == "Этот вопрос уже закрыт"


def test_daily_limit_stops_quiz(db, bot, dispatcher, monkeypatch):
    dispatcher["settings"] = Settings(bot="fat_joke", quiz_daily_limit=1)
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz"))
    picker_id = bot.session.next_message_id
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz мобла"))
    question_id = bot.session.next_message_id
    _, buttons = sent_question(bot)
    feed(dispatcher, bot, **press(user(7, "Alex"), question_id, buttons[0].callback_data))

    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz бух"))
    assert sent_texts(bot)[-1].startswith("На сегодня всё: 1 вопрос в день")
    feed(dispatcher, bot, **press(user(7, "Alex"), picker_id, "t geo 7"))
    alert = bot.session.of_type(methods.AnswerCallbackQuery)[-1]
    assert alert.show_alert and alert.text.startswith("На сегодня всё")
    assert db.fetch_one("SELECT COUNT(*) FROM QuizMessages")[0] == 1
    # the limit is per person
    feed(dispatcher, bot, **text_update(user(8, "Bob"), "/quiz бух"))
    assert sent_texts(bot)[-1].startswith("Бухгалтерия.")


def test_scheduled_question_is_for_everyone(db, bot, dispatcher):
    users_db.register(db, user(8, "Bob"))
    asyncio.run(ask_question(bot, db, CHAT.id))
    message_id = bot.session.next_message_id
    _, buttons = sent_question(bot)
    feed(dispatcher, bot, **press(user(8, "Bob"), message_id, buttons[0].callback_data))
    assert db.fetch_all("SELECT telegram_id FROM Answers") == [(8,)]


def test_quiz_command_without_topic_shows_picker(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz"))
    picker = bot.session.of_type(methods.SendMessage)[-1]
    buttons = {button.text: button.callback_data for row in picker.reply_markup.inline_keyboard for button in row}
    assert picker.text.startswith("Какую тему") and buttons["Бухгалтерия"] == "t accounting 7"
    picker_id = bot.session.next_message_id

    # Bob can't pick a topic on Alex's /quiz
    feed(dispatcher, bot, **press(user(8, "Bob"), picker_id, "t accounting 7"))
    assert bot.session.of_type(methods.AnswerCallbackQuery)[-1].text.startswith("Это не твой /quiz")
    assert quiz_db.get_open_question(db, CHAT.id) is None

    feed(dispatcher, bot, **press(user(7, "Alex"), picker_id, "t accounting 7"))
    edit = bot.session.of_type(methods.EditMessageText)[-1]
    assert edit.message_id == picker_id and edit.text.startswith("Бухгалтерия.") and edit.reply_markup
    assert quiz_db.get_open_question_of(db, CHAT.id, 7) == (picker_id,)

    # a second press on the same picker doesn't overwrite the question
    feed(dispatcher, bot, **press(user(7, "Alex"), picker_id, "t geo 7"))
    assert bot.session.of_type(methods.AnswerCallbackQuery)[-1].text == "Тему уже выбрали"
    assert quiz_db.get_open_question(db, CHAT.id, "geo") is None


def test_picker_refuses_topic_with_open_question(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz бух"))
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz"))
    feed(dispatcher, bot, **press(user(7, "Alex"), bot.session.next_message_id, "t geo 7"))
    assert bot.session.of_type(methods.AnswerCallbackQuery)[-1].show_alert
    assert len(db.fetch_all("SELECT 1 FROM QuizMessages")) == 1


def test_quiz_command_with_unknown_topic_shows_picker(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz ерунда"))
    message = bot.session.of_type(methods.SendMessage)[-1]
    assert message.text.startswith("Не знаю такой темы") and message.reply_markup


def test_leaders_for_a_named_topic(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/show_leaders бух"))
    assert bot.session.of_type(methods.SendMessage)[-1].text.startswith("Лидеры в дисциплине Бухгалтерия, сезон 1")
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/already_answered_questions гео"))
    assert bot.session.of_type(methods.SendMessage)[-1].text.startswith("Вот ленивая срака")


def test_leaders_of_all_topics(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/leaders"))
    text = bot.session.of_type(methods.SendMessage)[-1].text
    assert "Пока без лидеров:" in text and "Бухгалтерия" in text and "🥇" not in text

    for number, (user_id, discipline) in enumerate(
        [(7, "accounting"), (7, "accounting"), (8, "accounting"), (8, "geo")]
    ):
        db.execute(
            "INSERT INTO Answers (telegram_id, discipline, question_number, is_correct) VALUES (?, ?, ?, 1)",
            (user_id, discipline, number + 1),
        )
    users_db.register(db, user(8, "Bob"))
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/leaders"))
    # the inserted answers also bring Alex achievements, announced after the reply
    text = [text for text in sent_texts(bot) if text.startswith("🏆 Лидеры викторины")][-1]
    assert "Бухгалтерия, сезон 1:\n🥇 Alex — 2\n🥈 Bob — 1" in text
    assert "География, сезон 1:\n🥇 Bob — 1" in text
    assert "Бухгалтерия" not in text.split("Пока без лидеров:")[1]


def test_discipline_command(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/discipline"))
    assert "👉 mlbb2" in bot.session.of_type(methods.SendMessage)[-1].text

    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/discipline гео"))
    assert "только админы" in bot.session.of_type(methods.SendMessage)[-1].text
    assert quiz.current_discipline(db) == "mlbb2"

    bot.session.admins.add(7)
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/discipline nope"))
    assert "Не знаю такой темы" in bot.session.of_type(methods.SendMessage)[-1].text
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/discipline география"))
    assert quiz.current_discipline(db) == "geo"
    asyncio.run(scheduled_question(bot, db, chat_id=CHAT.id))
    assert bot.session.of_type(methods.SendMessage)[-1].text.startswith("География.")


def test_expired_question_is_closed_with_the_answer(db, bot):
    asyncio.run(ask_question(bot, db, CHAT.id))
    db.execute("UPDATE QuizMessages SET created_at = datetime('now', '-20 minutes')")
    asyncio.run(close_expired_questions(bot, db, minutes=15))
    edit = bot.session.of_type(methods.EditMessageText)[-1]
    assert edit.message_id == bot.session.next_message_id and "Время вышло" in edit.text
    assert quiz_db.get_open_question(db, CHAT.id) is None


def test_scheduled_question_skips_quiet_hours_and_open_questions(db, bot, monkeypatch):
    monkeypatch.setattr(scheduler_module, "is_quiet", lambda hour, quiet_hours: True)
    asyncio.run(scheduled_question(bot, db, CHAT.id, quiet_hours=(0, 24)))
    assert not bot.session.of_type(methods.SendMessage)

    monkeypatch.setattr(scheduler_module, "is_quiet", lambda hour, quiet_hours: False)
    asyncio.run(scheduled_question(bot, db, CHAT.id))
    asyncio.run(scheduled_question(bot, db, CHAT.id))
    assert len(bot.session.of_type(methods.SendMessage)) == 1


def test_season_end_is_announced(db, bot, monkeypatch):
    mlbb2 = quiz.disciplines()["mlbb2"]
    monkeypatch.setattr(quiz, "disciplines", lambda: {"mlbb2": mlbb2})
    for number in mlbb2.questions:
        quiz_db.save_quiz_message(db, CHAT.id, number, "mlbb2", 1, number)
    db.execute("UPDATE QuizMessages SET closed_at = CURRENT_TIMESTAMP")
    asyncio.run(ask_question(bot, db, CHAT.id))
    texts = [request.text for request in bot.session.of_type(methods.SendMessage)]
    assert texts[0].startswith("🏁 Сезон 1") and texts[1].startswith("MLBB 2.")


def test_old_buttons_are_closed(db, bot, dispatcher):
    feed(dispatcher, bot, **press(user(7, "Alex"), 1, "correct 5"))
    assert bot.session.of_type(methods.AnswerCallbackQuery)[-1].text == "Этот вопрос уже закрыт"
    assert not bot.session.of_type(methods.EditMessageText)


def test_ordinary_stickers_do_not_spam(db, bot, dispatcher, monkeypatch):
    monkeypatch.setattr(reactions, "sticker_replier", reactions.StickerReplier(chance=1))
    for message_id in range(3):
        sticker = {
            "file_id": "f",
            "file_unique_id": "u",
            "type": "regular",
            "width": 1,
            "height": 1,
            "is_animated": False,
            "is_video": False,
        }
        message = Message.model_validate(
            {
                "message_id": message_id,
                "date": datetime.now(),
                "chat": CHAT,
                "from": user(7, "Alex"),
                "sticker": sticker,
            }
        )
        feed(dispatcher, bot, message=message)
    assert len(bot.session.of_type(methods.SendMessage)) == 1


def test_scheduler_jobs(db, bot):
    async def job_ids(chat_id, miss_you, quiz_schedule=False):
        scheduler = create_scheduler(bot, db, chat_id, miss_you, quiz_schedule_enabled=quiz_schedule)
        return sorted(job.func.__name__ for job in scheduler.get_jobs())

    assert asyncio.run(job_ids("", False)) == [
        "close_duels",
        "close_expired_questions",
        "close_who_polls",
        "update_activity",
    ]
    # questions only on /quiz unless the schedule is switched on
    assert asyncio.run(job_ids(CHAT.id, False)) == [
        "close_duels",
        "close_expired_questions",
        "close_who_polls",
        "hourly_bam",
        "update_activity",
    ]
    scheduler = create_scheduler(bot, db, CHAT.id, quote_of_the_day_enabled=True)
    assert "quote_of_the_day" in [job.func.__name__ for job in scheduler.get_jobs()]
    assert "scheduled_question" in asyncio.run(job_ids(CHAT.id, False, quiz_schedule=True))
    assert "we_miss_you" in asyncio.run(job_ids(CHAT.id, True))
    scheduler = create_scheduler(bot, db, CHAT.id, weekly_summary_enabled=True, who_poll_enabled=True)
    assert {"weekly_summary", "who_poll"} <= {job.func.__name__ for job in scheduler.get_jobs()}


def test_scheduler_backup_job(db, bot, tmp_path):
    async def backup_job():
        scheduler = create_scheduler(bot, db, "", db_path=tmp_path / "bot.db", backup_dir=tmp_path / "backups")
        return next(job for job in scheduler.get_jobs() if job.func.__name__ == "backup")

    assert asyncio.run(backup_job()).misfire_grace_time >= 12 * 60 * 60


def test_chat_id_command(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/chat_id"))
    assert bot.session.of_type(methods.SendMessage)[-1].text == f"ID этого чата: {CHAT.id}"


def test_missing_chat_is_logged_not_raised(db, bot, caplog):
    bot.session.missing_chats.add(CHAT.id)
    asyncio.run(hourly_bam(bot, db, chat_id=CHAT.id))
    asyncio.run(scheduled_question(bot, db, chat_id=CHAT.id))
    assert caplog.text.count("chat not found") == 2 and "FAT_JOKE_MAIN_CHAT_ID" in caplog.text
    assert quiz_db.get_open_question(db, CHAT.id) is None


def test_check_chat(db, bot, caplog):
    assert asyncio.run(check_chat(bot, CHAT.id))
    bot.session.left_chats.add(CHAT.id)
    assert not asyncio.run(check_chat(bot, CHAT.id))
    bot.session.missing_chats.add(-1)
    assert not asyncio.run(check_chat(bot, -1))
    assert "has left it" in caplog.text and "chat not found" in caplog.text


def test_command_menu_has_a_handler_for_every_command(bot):
    handled = {
        name
        for router in main.ROUTERS
        for handler in router.message.handlers
        for command_filter in handler.filters
        for name in getattr(command_filter.callback, "commands", ())
    }
    assert set(bot_commands) <= handled
    asyncio.run(main.set_commands(bot))
    sent = bot.session.of_type(methods.SetMyCommands)[-1]
    assert [command.command for command in sent.commands] == list(bot_commands)


def answers(bot):
    return [request.text for request in bot.session.of_type(methods.AnswerCallbackQuery)]


def test_quote_book(db, bot, dispatcher):
    alex, sergio = user(7, "Alex"), user(8, "Sergio")
    feed(dispatcher, bot, **text_update(alex, "/quote"))
    feed(dispatcher, bot, **text_update(alex, "/save"))
    feed(dispatcher, bot, **reply_update(alex, "/save", sergio, "Я на диете с понедельника"))
    feed(dispatcher, bot, **reply_update(alex, "/save", sergio, "Я на диете с понедельника"))
    feed(dispatcher, bot, **text_update(alex, "/quote SERG"))
    feed(dispatcher, bot, **text_update(alex, "/quote Вася"))
    texts = sent_texts(bot)
    assert texts[0].startswith("Цитатник пока пуст")
    assert texts[1].startswith("Ответь командой /save")
    assert texts[2].endswith("Всего цитат: 1")
    assert texts[3] == "Эта цитата уже в цитатнике 📜"
    today = datetime.now(KYIV).strftime("%d.%m.%Y")
    assert texts[4] == f"«Я на диете с понедельника»\n— Sergio (@sergio), {today}"
    assert texts[5] == "У «Вася» цитат пока нет 🤔"


def test_quote_of_the_day_goes_through_every_quote(db, bot, dispatcher):
    asyncio.run(quote_of_the_day(bot, db, chat_id=CHAT.id))
    assert sent_texts(bot) == []
    for number, phrase in enumerate(("Раз", "Два")):
        save = reply_update(
            user(7, "Alex"), "/save", user(8, "Sergio"), phrase, message_id=10 + number, original_id=number
        )
        feed(dispatcher, bot, **save)
    for _ in range(2):
        asyncio.run(quote_of_the_day(bot, db, chat_id=CHAT.id))
    shown = [text for text in sent_texts(bot) if text.startswith("📜 Цитата дня")]
    assert len(shown) == 2 and {text.split("\n")[2] for text in shown} == {"«Раз»", "«Два»"}


def test_fat_of_the_day_once_a_day(db, bot, dispatcher, monkeypatch):
    monkeypatch.setattr(fat_day_handlers, "SCAN_PAUSE_SECONDS", 0)
    feed(dispatcher, bot, **text_update(user(8, "Sergio"), "привет"))
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/fat"))
    texts = sent_texts(bot)
    assert len(texts) == 4
    winner = "Alex" if "Alex" in texts[-1] else "Sergio"
    assert f"{winner} (@{winner.lower()})" in texts[-1]

    feed(dispatcher, bot, **text_update(user(8, "Sergio"), "/fat"))
    assert len(sent_texts(bot)) == 5 and winner in sent_texts(bot)[-1]
    feed(dispatcher, bot, **text_update(user(8, "Sergio"), "/fatstats"))
    assert f"🥇 {winner} — 1 раз" in sent_texts(bot)[-1]


def test_party_gathers_five_and_pings_them(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(1, "P1"), "/party ранкед в 21:00"))
    party_message = bot.session.next_message_id
    first = bot.session.of_type(methods.SendPhoto)[-1]
    assert first.photo == reaction_data.party_photo
    assert "ранкед в 21:00" in first.caption and "1. P1 (@p1)" in first.caption and first.reply_markup

    feed(dispatcher, bot, **text_update(user(2, "P2"), "/party"))
    again = bot.session.of_type(methods.SendMessage)[-1]
    assert again.text.startswith("Пати уже собирается") and again.reply_parameters.message_id == party_message

    feed(dispatcher, bot, **press(user(1, "P1"), party_message, party.JOIN, photo=True))
    feed(dispatcher, bot, **press(user(2, "P2"), party_message, party.LEAVE, photo=True))
    for number in (2, 3, 4):
        feed(dispatcher, bot, **press(user(number, f"P{number}"), party_message, party.JOIN, photo=True))
    feed(dispatcher, bot, **press(user(4, "P4"), party_message, party.LEAVE, photo=True))
    assert answers(bot)[:2] == ["Ты уже в пати 😉", "Тебя и так нет в пати 🤷"]
    assert "В деле 3/5" in bot.session.of_type(methods.EditMessageCaption)[-1].caption
    assert not bot.session.of_type(methods.SendMessage)[-1].entities

    for number in (4, 5):
        feed(dispatcher, bot, **press(user(number, f"P{number}"), party_message, party.JOIN, photo=True))
    edit = bot.session.of_type(methods.EditMessageCaption)[-1]
    assert "В деле 5/5" in edit.caption and "Пати собрана" in edit.caption and edit.reply_markup is None
    call = bot.session.of_type(methods.SendMessage)[-1]
    assert "пати собрана, заходим" in call.text
    assert sorted(entity.user.id for entity in call.entities) == [1, 2, 3, 4, 5]

    feed(dispatcher, bot, **press(user(6, "P6"), party_message, party.JOIN, photo=True))
    assert answers(bot)[-1] == "Пати уже собрана 🎮"
    # the gathered party doesn't block a new one
    feed(dispatcher, bot, **text_update(user(6, "P6"), "/party"))
    assert "1. P6" in bot.session.of_type(methods.SendPhoto)[-1].caption


def test_party_for_two(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(1, "P1"), "/party 2 ранкед"))
    party_message = bot.session.next_message_id
    first = bot.session.of_type(methods.SendPhoto)[-1]
    assert "В деле 1/2" in first.caption and "ранкед" in first.caption and "2 ранкед" not in first.caption

    feed(dispatcher, bot, **press(user(2, "P2"), party_message, party.JOIN, photo=True))
    edit = bot.session.of_type(methods.EditMessageCaption)[-1]
    assert "В деле 2/2" in edit.caption and "Пати собрана" in edit.caption and edit.reply_markup is None
    call = bot.session.of_type(methods.SendMessage)[-1]
    assert sorted(entity.user.id for entity in call.entities) == [1, 2]


def test_old_party_falls_apart(db, bot, dispatcher, monkeypatch):
    # a party without a picture, like ServoSkull's, is edited as plain text
    monkeypatch.setattr(reaction_data, "party_photo", None)
    feed(dispatcher, bot, **text_update(user(1, "P1"), "/party"))
    party_message = bot.session.next_message_id
    db.execute("UPDATE Parties SET created_at = datetime('now', '-20 minutes')")
    feed(dispatcher, bot, **press(user(3, "P3"), party_message, party.JOIN))
    assert answers(bot)[-1] == "Ты в деле! 🎮"
    db.execute("UPDATE Parties SET created_at = datetime('now', '-31 minutes')")
    feed(dispatcher, bot, **press(user(2, "P2"), party_message, party.JOIN))
    assert answers(bot)[-1].startswith("Эта пати уже не работает")
    assert "Не собрались за 30 минут" in bot.session.of_type(methods.EditMessageText)[-1].text
    feed(dispatcher, bot, **press(user(2, "P2"), 12345, party.JOIN))
    assert answers(bot)[-1].startswith("Эта пати уже не работает")


def in_chat(db):
    return dict(db.fetch_all("SELECT telegram_id, in_chat FROM Users"))


def member_update(member_user, old, new):
    event = ChatMemberUpdated(
        chat=CHAT, from_user=member_user, date=datetime.now(), old_chat_member=old, new_chat_member=new
    )
    return {"chat_member": event}


def test_joins_and_leaves_are_tracked(db, bot, dispatcher):
    alex, newbie = user(7, "Alex"), user(8, "Newbie")
    added = Message(message_id=5, date=datetime.now(), chat=CHAT, from_user=alex, new_chat_members=[newbie, BOT_USER])
    feed(dispatcher, bot, message=added)
    assert in_chat(db) == {7: 1, 8: 1}

    gone = Message(message_id=6, date=datetime.now(), chat=CHAT, from_user=newbie, left_chat_member=newbie)
    feed(dispatcher, bot, message=gone)
    assert in_chat(db)[8] == 0
    # a left member drops out of the IQ table and the fatty of the day
    assert users_db.get_all_iq(db) == [("Alex", 100)]
    assert [row[0] for row in users_db.get_active_since(db, datetime(2000, 1, 1))] == [7]

    # the same through chat_member updates, which come even when join messages are hidden
    feed(dispatcher, bot, **member_update(newbie, ChatMemberLeft(user=newbie), ChatMemberMember(user=newbie)))
    assert in_chat(db)[8] == 1
    feed(dispatcher, bot, **member_update(newbie, ChatMemberMember(user=newbie), ChatMemberLeft(user=newbie)))
    assert in_chat(db)[8] == 0
    # writing in the group again brings them back
    feed(dispatcher, bot, **text_update(newbie, "я вернулся"))
    assert in_chat(db)[8] == 1


def test_members_command(db, bot, dispatcher):
    for user_id in (7, 8, 9, 10):
        feed(dispatcher, bot, **text_update(user(user_id, f"Old{user_id}"), "привет"))
    bot.session.left_users.add(8)
    bot.session.unknown_users.add(9)
    bot.session.muted_users.add(10)

    feed(dispatcher, bot, **text_update(user(7, "Old7"), "/members"))
    assert sent_texts(bot)[-1] == "Проверять участников могут только админы чата 😈"
    assert in_chat(db) == {7: 1, 8: 1, 9: 1, 10: 1}

    bot.session.admins.add(7)
    feed(dispatcher, bot, **text_update(user(7, "Old7"), "/members"))
    report = sent_texts(bot)[-1]
    # names and usernames come fresh from Telegram, the unknown user keeps the old ones
    assert "В чате (2):\n• Name7 — 7\n• Name10 — 10" in report
    assert "Ушли (2):\n• Name8 — 8\n• Old9 (@old9) — 9" in report
    assert in_chat(db) == {7: 1, 8: 0, 9: 0, 10: 1}


def test_main_starts_up_to_polling(tmp_path, monkeypatch):
    """Runs the real main() until it asks Telegram for updates, catching startup errors the other tests skip."""

    class StopAtPolling(FakeSession):
        async def make_request(self, bot, method, timeout=None):
            if isinstance(method, methods.GetUpdates):
                self.allowed_updates = method.allowed_updates
                raise asyncio.CancelledError
            return await super().make_request(bot, method, timeout)

    session = StopAtPolling()
    monkeypatch.setattr(main, "Bot", lambda token: Bot("42:TEST", session=session))
    settings = Settings(
        bot="fat_joke",
        # CI has no .env, the token is never used by the fake session anyway
        token="42:TEST",
        db_path=str(tmp_path / "bot.db"),
        backup_dir=str(tmp_path / "backups"),
        main_chat_id=str(CHAT.id),
        quote_of_the_day_enabled=True,
    )
    try:
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(main.main(settings))
    finally:
        for router in main.ROUTERS:
            router._parent_router = None
    assert "chat_member" in session.allowed_updates


def bam_with_loot(bot, db, code):
    asyncio.run(hourly_bam(bot, db, chat_id=CHAT.id, rng=LootRandom(code)))
    sent = bot.session.of_type(methods.SendMessage)[-1]
    return sent, bot.session.next_message_id


def test_bam_loot_goes_to_the_fastest(db, bot, dispatcher):
    sent, message_id = bam_with_loot(bot, db, "turtle")
    assert "🐢 Заспавнилась Черепаха!" in sent.text and "+10 BP" in sent.text
    assert sent.reply_markup.inline_keyboard[0][0].callback_data == loot.CALLBACK

    press_loot(dispatcher, bot, user(7, "Alex"), message_id, sent.text)
    press_loot(dispatcher, bot, user(8, "Bob"), message_id, sent.text)
    assert answers(bot)[0] == "+10 BP! 💰" and answers(bot)[1] in late_phrases
    edit = bot.session.of_type(methods.EditMessageText)[-1]
    assert edit.text.startswith("Бам!!!") and "Черепаху добил(а) Alex (@alex): +10 BP" in edit.text
    assert "Заспавнилась" not in edit.text and edit.reply_markup is None
    assert achievements.battle_points(db, 7) == 10 and achievements.battle_points(db, 8) == 0


def test_old_loot_is_gone(db, bot, dispatcher):
    sent, message_id = bam_with_loot(bot, db, "red")
    db.execute("UPDATE Loot SET created_at = datetime('now', '-3 hours')")
    press_loot(dispatcher, bot, user(7, "Alex"), message_id, sent.text)
    assert answers(bot)[-1] == gone_phrase
    assert "туман войны" in bot.session.of_type(methods.EditMessageText)[-1].text
    assert achievements.battle_points(db, 7) == 0


def test_no_loot_in_quiet_hours(db, bot):
    asyncio.run(hourly_bam(bot, db, chat_id=CHAT.id, quiet_hours=(0, 24), rng=LootRandom("lord")))
    assert bot.session.of_type(methods.SendMessage)[-1].reply_markup is None
    assert db.fetch_one("SELECT COUNT(*) FROM Loot")[0] == 0


def test_lord_gives_an_achievement_and_shows_in_profile(db, bot, dispatcher):
    sent, message_id = bam_with_loot(bot, db, "lord")
    press_loot(dispatcher, bot, user(7, "Alex"), message_id, sent.text)
    announced = sent_texts(bot)[-1]
    assert "Alex (@alex)" in announced and "🐉 Убийца Лорда" in announced and "+20 BP" in announced
    # 25 for the Lord and 20 for the achievement, Elite starts at 50
    assert achievements.battle_points(db, 7) == 45

    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/me"))
    profile = sent_texts(bot)[-1]
    assert profile.startswith("👤 Alex") and "Warrior, 45 BP" in profile and "до 🛡 Elite: ещё 5 BP" in profile
    assert "Достижения 1/" in profile and "🔒 First Blood" in profile and "Лордов: 1" in profile

    feed(dispatcher, bot, **reply_update(user(8, "Bob"), "/me", user(7, "Alex"), "я забрал лорда"))
    assert sent_texts(bot)[-1].startswith("👤 Alex")
    feed(dispatcher, bot, **text_update(user(8, "Bob"), "/ranks"))
    assert "🥇 Alex — 45 BP" in sent_texts(bot)[-1] and "🥈 Bob — 0 BP" in sent_texts(bot)[-1]
    # announced once
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "привет"))
    assert sum("Убийца Лорда" in text for text in sent_texts(bot) if not text.startswith("👤")) == 1


def test_quiet_week(db, bot):
    asyncio.run(weekly_summary(bot, db, chat_id=CHAT.id))
    assert "Тихая неделя" in sent_texts(bot)[-1]


def test_weekly_summary(db, bot, dispatcher, monkeypatch):
    monkeypatch.setattr(fat_day_handlers, "SCAN_PAUSE_SECONDS", 0)
    users_db.register(db, user(9, "Ghost"))
    for number in range(12):
        feed(dispatcher, bot, **text_update(user(7, "Alex"), f"сообщение {number}", message_id=100 + number))
    feed(dispatcher, bot, **text_update(user(8, "Bob"), "привет"))
    sent, message_id = bam_with_loot(bot, db, "lord")
    press_loot(dispatcher, bot, user(8, "Bob"), message_id, sent.text)
    feed(dispatcher, bot, **reply_update(user(7, "Alex"), "/save", user(8, "Bob"), "Я на диете", message_id=200))
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/fat"))

    feed(dispatcher, bot, **text_update(user(8, "Bob"), "/week"))
    summary = sent_texts(bot)[-1]
    assert summary.startswith("📅 Итоги недели")
    # Alex: 12 messages and /save, /fat; Bob: "привет" and /week
    assert "🥇 Alex — 14 сообщений" in summary and "🥈 Bob — 2 сообщения" in summary
    assert "Всего в чате: 16 сообщений" in summary
    assert "🥇 Bob — 25 BP, Лордов: 1" in summary
    assert "Bob: 🐉 Убийца Лорда" in summary
    assert "🍩 Жиртресты недели:" in summary and "«Я на диете»" in summary
    assert "🦗 Молчуны недели: Ghost (@ghost)" in summary
    assert "👑 MVP недели: Bob!" in summary


def test_who_poll(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/who"))
    assert sent_texts(bot)[-1].startswith("Для опроса нужно хотя бы двое")

    feed(dispatcher, bot, **text_update(user(8, "Bob"), "привет"))
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/who"))
    poll = bot.session.of_type(methods.SendPoll)[-1]
    poll_id = bot.session.next_message_id
    assert poll.question.startswith("Кто из нас ") and sorted(poll.options) == ["Alex", "Bob"]
    assert poll.is_anonymous is False

    # one poll at a time, the scheduled one too
    feed(dispatcher, bot, **text_update(user(8, "Bob"), "/who"))
    assert sent_texts(bot)[-1].startswith("Опрос уже идёт") and len(bot.session.of_type(methods.SendPoll)) == 1
    asyncio.run(who_poll(bot, db, chat_id=CHAT.id))
    assert len(bot.session.of_type(methods.SendPoll)) == 1

    # not closed before its time
    asyncio.run(close_who_polls(bot, db))
    assert not bot.session.of_type(methods.StopPoll)

    db.execute("UPDATE WhoPolls SET created_at = datetime('now', '-4 hours')")
    winner = poll.options.index("Bob")
    bot.session.poll_votes = [2 if index == winner else 1 for index in range(2)]
    asyncio.run(close_who_polls(bot, db))
    assert bot.session.of_type(methods.StopPoll)[-1].message_id == poll_id
    announce = bot.session.of_type(methods.SendMessage)[-1]
    assert f"«{poll.question}»" in announce.text and "это Bob! 2 голоса 🏆" in announce.text
    assert announce.entities[0].user.id == 8 and announce.reply_parameters.message_id == poll_id
    asyncio.run(close_who_polls(bot, db))
    assert len(bot.session.of_type(methods.StopPoll)) == 1

    # the next poll asks a new question
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/who"))
    assert bot.session.of_type(methods.SendPoll)[-1].question != poll.question


def duel_row(db):
    return duel.from_row(db.fetch_one(f"SELECT {DUEL_COLUMNS} FROM Duels ORDER BY id DESC LIMIT 1"))


def duel_buttons(bot):
    markup = bot.session.of_type(methods.EditMessageText)[-1].reply_markup
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def test_duel_needs_an_opponent(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/duel"))
    assert sent_texts(bot)[-1].startswith("Кого вызываешь?")
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/duel @nobody"))
    assert sent_texts(bot)[-1] == "Не знаю такого человека в чате 🤔"
    feed(dispatcher, bot, **reply_update(user(7, "Alex"), "/duel", user(7, "Alex"), "я"))
    assert sent_texts(bot)[-1].startswith("Дуэль с самим собой?")


def test_duel_round(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(8, "Bob"), "привет"))
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/duel @BOB мобла"))
    challenge = bot.session.of_type(methods.SendMessage)[-1]
    duel_message = bot.session.next_message_id
    assert challenge.text.startswith("⚔️ Alex (@alex) вызывает Bob (@bob) на дуэль по теме MLBB 2!")
    accept, decline = [button.callback_data for button in challenge.reply_markup.inline_keyboard[0]]

    # a second duel for either of them waits
    feed(dispatcher, bot, **text_update(user(9, "Eve"), "/duel @bob"))
    assert sent_texts(bot)[-1] == "У соперника уже есть незаконченная дуэль ⚔️"
    # only Bob can accept
    feed(dispatcher, bot, **press(user(9, "Eve"), duel_message, accept))
    feed(dispatcher, bot, **press(user(7, "Alex"), duel_message, accept))
    assert answers(bot)[-2:] == ["Это не тебя вызвали 🍿", "Это не тебя вызвали 🍿"]

    feed(dispatcher, bot, **press(user(8, "Bob"), duel_message, accept))
    asked = bot.session.of_type(methods.EditMessageText)[-1]
    assert asked.text.startswith("⚔️ Дуэль: Alex (@alex) vs Bob (@bob)") and "MLBB 2." in asked.text
    current = duel_row(db)
    question = quiz.get_question(current.discipline, current.question_number)
    by_option = {duel.parse_callback(data)[2]: data for data in duel_buttons(bot)}
    right = by_option[min(question.correct)]
    wrong = next(data for option, data in by_option.items() if option not in question.correct)

    feed(dispatcher, bot, **press(user(9, "Eve"), duel_message, right))
    assert answers(bot)[-1].startswith("Ты не участвуешь")
    feed(dispatcher, bot, **press(user(8, "Bob"), duel_message, wrong))
    feed(dispatcher, bot, **press(user(8, "Bob"), duel_message, right))
    assert answers(bot)[-2:] == ["Ответ принят, ждём соперника ⏳", "Ты уже ответил(а), ждём соперника ⏳"]
    feed(dispatcher, bot, **press(user(7, "Alex"), duel_message, right))
    result = bot.session.of_type(methods.EditMessageText)[-1].text
    assert "✅ Alex (@alex):" in result and "❌ Bob (@bob):" in result
    assert "🏆 Побеждает Alex (@alex)! +10 BP" in result
    assert achievements.battle_points(db, 7) == 10 and achievements.battle_points(db, 8) == 0
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/me"))
    assert "🤺 Побед в дуэлях: 1" in sent_texts(bot)[-1]
    # finished, a new one is possible
    feed(dispatcher, bot, **text_update(user(8, "Bob"), "/duel @alex"))
    assert sent_texts(bot)[-1].startswith("⚔️ Bob (@bob) вызывает Alex (@alex)")


def test_duel_declined(db, bot, dispatcher):
    feed(dispatcher, bot, **reply_update(user(7, "Alex"), "/duel", user(8, "Bob"), "ну давай"))
    duel_message = bot.session.next_message_id
    feed(dispatcher, bot, **press(user(8, "Bob"), duel_message, duel.challenge_callback(duel_row(db).id, "no")))
    assert bot.session.of_type(methods.EditMessageText)[-1].text == "🏳️ Bob (@bob) отказался(ась) от дуэли."
    assert duel_row(db).status == "declined"


def test_duel_timeouts(db, bot, dispatcher):
    feed(dispatcher, bot, **reply_update(user(7, "Alex"), "/duel", user(8, "Bob"), "ну давай"))
    db.execute("UPDATE Duels SET created_at = datetime('now', '-11 minutes')")
    asyncio.run(close_duels(bot, db))
    assert "так и не принял(а) вызов" in bot.session.of_type(methods.EditMessageText)[-1].text

    feed(dispatcher, bot, **reply_update(user(7, "Alex"), "/duel", user(8, "Bob"), "ещё раз", message_id=5))
    duel_message = bot.session.next_message_id
    feed(dispatcher, bot, **press(user(8, "Bob"), duel_message, duel.challenge_callback(duel_row(db).id, "yes")))
    current = duel_row(db)
    question = quiz.get_question(current.discipline, current.question_number)
    feed(
        dispatcher, bot, **press(user(8, "Bob"), duel_message, duel.answer_callback(current.id, min(question.correct)))
    )
    asyncio.run(close_duels(bot, db))
    assert duel_row(db).status == "active"
    db.execute("UPDATE Duels SET started_at = started_at - 300")
    asyncio.run(close_duels(bot, db))
    result = bot.session.of_type(methods.EditMessageText)[-1].text
    assert "😴 Alex (@alex) не успел(а) ответить" in result and "Побеждает Bob (@bob)" in result


def give_bp(db, user_id, points):
    db.execute(
        "INSERT INTO Loot (chat_id, message_id, kind, points, taken_by) VALUES (?, ?, 'red', ?, ?)",
        (CHAT.id, 9000 + user_id, points, user_id),
    )


def test_bets_on_a_duel(db, bot, dispatcher):
    for user_id, name in ((8, "Bob"), (9, "Eve"), (10, "Max"), (11, "Ann")):
        feed(dispatcher, bot, **text_update(user(user_id, name), "привет"))
    give_bp(db, 9, 100)
    give_bp(db, 10, 100)
    give_bp(db, 11, 5)
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/duel @bob"))
    duel_message = bot.session.next_message_id
    challenge = bot.session.of_type(methods.SendMessage)[-1]
    assert "💰 Ставок пока нет" in challenge.text
    bet_buttons = {b.text: b.callback_data for b in challenge.reply_markup.inline_keyboard[1]}
    on_alex, on_bob = bet_buttons["💰 +10 на Alex"], bet_buttons["💰 +10 на Bob"]

    feed(dispatcher, bot, **press(user(7, "Alex"), duel_message, on_alex))
    assert answers(bot)[-1] == "Дуэлянтам ставить нельзя, это договорняк 😏"
    feed(dispatcher, bot, **press(user(11, "Ann"), duel_message, on_alex))
    assert answers(bot)[-1] == "Не хватает BP: у тебя 5 BP"
    feed(dispatcher, bot, **press(user(9, "Eve"), duel_message, on_alex))
    feed(dispatcher, bot, **press(user(9, "Eve"), duel_message, on_alex))
    assert answers(bot)[-1] == "Ставка принята! Всего 20 BP 💰"
    assert "💰 Банк: 20 BP (на Alex 20, на Bob 0)" in bot.session.of_type(methods.EditMessageText)[-1].text
    feed(dispatcher, bot, **press(user(9, "Eve"), duel_message, on_bob))
    assert answers(bot)[-1].startswith("Ты уже поставил(а) на другого")
    feed(dispatcher, bot, **text_update(user(10, "Max"), "/bet 40 @bob"))
    assert sent_texts(bot)[-1] == "💰 Max ставит 40 BP на Bob!"
    feed(dispatcher, bot, **text_update(user(10, "Max"), "/bet 20 @bob"))
    assert sent_texts(bot)[-1] == f"Не больше {bets.MAX_BET} BP на одну дуэль"
    assert achievements.battle_points(db, 10) == 60

    feed(dispatcher, bot, **press(user(8, "Bob"), duel_message, duel.challenge_callback(duel_row(db).id, "yes")))
    feed(dispatcher, bot, **text_update(user(10, "Max"), "/bet 5 @bob"))
    assert sent_texts(bot)[-1].startswith("У Bob сейчас нет дуэли")
    current = duel_row(db)
    question = quiz.get_question(current.discipline, current.question_number)
    wrong = next(option for option in range(4) if option not in question.correct)
    feed(
        dispatcher, bot, **press(user(7, "Alex"), duel_message, duel.answer_callback(current.id, min(question.correct)))
    )
    feed(dispatcher, bot, **press(user(8, "Bob"), duel_message, duel.answer_callback(current.id, wrong)))
    result = bot.session.of_type(methods.EditMessageText)[-1].text
    # Eve bet 20 on Alex and takes Max's 40
    assert result.endswith("💰 Ставки:\nEve: +40 BP\nMax: −40 BP")
    assert achievements.battle_points(db, 9) == 140 and achievements.battle_points(db, 10) == 60


def test_bets_come_back_when_the_duel_is_off(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(9, "Eve"), "привет"))
    give_bp(db, 9, 30)
    feed(dispatcher, bot, **reply_update(user(7, "Alex"), "/duel", user(8, "Bob"), "ну давай"))
    feed(dispatcher, bot, **text_update(user(9, "Eve"), "/bet 30 @alex"))
    assert achievements.battle_points(db, 9) == 0
    feed(dispatcher, bot, **press(user(8, "Bob"), bot.session.next_message_id - 1, duel.challenge_callback(1, "no")))
    assert bot.session.of_type(methods.EditMessageText)[-1].text.endswith("💰 Ставки вернули.")
    assert achievements.battle_points(db, 9) == 30
