"""Feeds real Telegram updates through the aiogram dispatcher, with a fake session instead of the network."""

import asyncio
from datetime import datetime

import pytest
from aiogram import Bot, methods
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    Chat,
    ChatMemberLeft,
    ChatMemberMember,
    ChatMemberOwner,
    ChatMemberRestricted,
    ChatMemberUpdated,
    Message,
    Update,
    User,
)

from telegram_bots.bots.fat_joke import main
from telegram_bots.bots.fat_joke import scheduler as scheduler_module
from telegram_bots.bots.fat_joke.db import quiz as quiz_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.handlers import fat_day as fat_day_handlers
from telegram_bots.bots.fat_joke.handlers import reactions
from telegram_bots.bots.fat_joke.scheduler import (
    ask_question,
    check_chat,
    close_expired_questions,
    create_scheduler,
    hourly_bam,
    quote_of_the_day,
    scheduled_question,
)
from telegram_bots.bots.fat_joke.services import party, quiz
from telegram_bots.knowledge_base.fat_joke.reaction_data import bot_commands, red_blink

CHAT = Chat(id=-100500, type="supergroup", title="Test chat")
BOT_USER = User(id=42, is_bot=True, first_name="FatJoke", username="fat_joke_bot")


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.requests = []
        self.next_message_id = 1000
        self.admins = set()
        self.missing_chats = set()
        self.left_chats = set()
        self.left_users = set()
        self.muted_users = set()
        self.unknown_users = set()

    async def make_request(self, bot, method, timeout=None):
        self.requests.append(method)
        if getattr(method, "chat_id", None) in self.missing_chats:
            raise TelegramBadRequest(method=method, message="Bad Request: chat not found")
        if isinstance(method, methods.GetChatMember) and method.chat_id in self.left_chats:
            return ChatMemberLeft(user=BOT_USER)
        if isinstance(method, methods.GetMe):
            return BOT_USER
        if isinstance(method, methods.GetChatMember) and method.user_id in self.unknown_users:
            raise TelegramBadRequest(method=method, message="Bad Request: PARTICIPANT_ID_INVALID")
        if isinstance(method, methods.GetChatMember):
            member_user = User(id=method.user_id, is_bot=False, first_name=f"Name{method.user_id}")
            if method.user_id in self.left_users:
                return ChatMemberLeft(user=member_user)
            if method.user_id in self.muted_users:
                return muted(member_user)
            if method.user_id in self.admins:
                return ChatMemberOwner(user=member_user, is_anonymous=False)
            return ChatMemberMember(user=member_user)
        if isinstance(method, (methods.SendMessage, methods.SendSticker, methods.SendAnimation, methods.SendPhoto)):
            self.next_message_id += 1
            return Message(message_id=self.next_message_id, date=datetime.now(), chat=CHAT, from_user=BOT_USER)
        return True

    async def stream_content(self, *args, **kwargs):
        yield b""

    async def close(self):
        pass

    def of_type(self, method_type):
        return [request for request in self.requests if isinstance(request, method_type)]


def muted(member_user):
    # every can_* right off, taken from the model so new Bot API rights don't break the test
    rights = {name: False for name in ChatMemberRestricted.model_fields if name.startswith("can_")}
    return ChatMemberRestricted(user=member_user, is_member=True, until_date=datetime.now(), **rights)


@pytest.fixture(autouse=True)
def no_philosophy(monkeypatch):
    # a random philosopher quote on any text message would add an unexpected reply now and then
    monkeypatch.setattr("telegram_bots.bots.fat_joke.services.reactions.PHILOSOPHY_CHANCE", 0)


@pytest.fixture
def bot():
    return Bot("42:TEST", session=FakeSession())


@pytest.fixture
def dispatcher(db):
    yield main.build_dispatcher(db)
    # module level routers can belong to one dispatcher only, detach them for the next test
    for router in main.ROUTERS:
        router._parent_router = None


def user(user_id, name):
    return User(id=user_id, is_bot=False, first_name=name, username=name.lower())


def feed(dispatcher, bot, **update):
    asyncio.run(dispatcher.feed_update(bot, Update(update_id=1, **update)))


def text_update(from_user, text, message_id=1):
    return {"message": Message(message_id=message_id, date=datetime.now(), chat=CHAT, from_user=from_user, text=text)}


def reply_update(from_user, text, original_author, original_text, message_id=2, original_id=1):
    original = Message(
        message_id=original_id, date=datetime.now(), chat=CHAT, from_user=original_author, text=original_text
    )
    message = Message(
        message_id=message_id, date=datetime.now(), chat=CHAT, from_user=from_user, text=text, reply_to_message=original
    )
    return {"message": message}


def press(from_user, message_id, data):
    message = Message(message_id=message_id, date=datetime.now(), chat=CHAT, from_user=BOT_USER, text="?")
    return {"callback_query": CallbackQuery(id="1", from_user=from_user, chat_instance="c", message=message, data=data)}


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


def sent_question(bot):
    message = bot.session.of_type(methods.SendMessage)[-1]
    buttons = [button for row in message.reply_markup.inline_keyboard for button in row]
    return message, buttons


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


def test_quiz_command_with_topic_asks_once_per_topic(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz мобла"))
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz по мобле"))
    feed(dispatcher, bot, **text_update(user(8, "Bob"), "/quiz по бухгалтерии"))
    texts = [request.text for request in bot.session.of_type(methods.SendMessage)]
    assert texts[0].startswith("MLBB 2.")
    assert texts[1].startswith("Сначала ответьте на предыдущий вопрос по теме MLBB 2")
    assert texts[2].startswith("Бухгалтерия.")
    assert {row[0] for row in db.fetch_all("SELECT discipline FROM QuizMessages")} == {"mlbb2", "accounting"}


def test_quiz_command_without_topic_shows_picker(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz"))
    picker = bot.session.of_type(methods.SendMessage)[-1]
    buttons = {button.text: button.callback_data for row in picker.reply_markup.inline_keyboard for button in row}
    assert picker.text.startswith("Какую тему") and buttons["Бухгалтерия"] == "t accounting"
    picker_id = bot.session.next_message_id

    feed(dispatcher, bot, **press(user(8, "Bob"), picker_id, "t accounting"))
    edit = bot.session.of_type(methods.EditMessageText)[-1]
    assert edit.message_id == picker_id and edit.text.startswith("Бухгалтерия.") and edit.reply_markup
    assert quiz_db.get_open_question(db, CHAT.id, "accounting") == (picker_id,)

    # a second press on the same picker doesn't overwrite the question
    feed(dispatcher, bot, **press(user(7, "Alex"), picker_id, "t geo"))
    assert bot.session.of_type(methods.AnswerCallbackQuery)[-1].text == "Тему уже выбрали"
    assert quiz_db.get_open_question(db, CHAT.id, "geo") is None


def test_picker_refuses_topic_with_open_question(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz бух"))
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/quiz"))
    feed(dispatcher, bot, **press(user(7, "Alex"), bot.session.next_message_id, "t accounting"))
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
    monkeypatch.setattr(quiz, "DISCIPLINES", {"mlbb2": quiz.DISCIPLINES["mlbb2"]})
    for number in quiz.DISCIPLINES["mlbb2"].questions:
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

    assert asyncio.run(job_ids("", False)) == ["close_expired_questions", "update_activity"]
    # questions only on /quiz unless the schedule is switched on
    assert asyncio.run(job_ids(CHAT.id, False)) == ["close_expired_questions", "hourly_bam", "update_activity"]
    scheduler = create_scheduler(bot, db, CHAT.id, quote_of_the_day_enabled=True)
    assert "quote_of_the_day" in [job.func.__name__ for job in scheduler.get_jobs()]
    assert "scheduled_question" in asyncio.run(job_ids(CHAT.id, False, quiz_schedule=True))
    assert "we_miss_you" in asyncio.run(job_ids(CHAT.id, True))


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
    asyncio.run(hourly_bam(bot, chat_id=CHAT.id))
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


def sent_texts(bot):
    return [request.text for request in bot.session.of_type(methods.SendMessage)]


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
    today = datetime.now().strftime("%d.%m.%Y")
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
    first = bot.session.of_type(methods.SendMessage)[-1]
    assert "ранкед в 21:00" in first.text and "1. P1 (@p1)" in first.text and first.reply_markup

    feed(dispatcher, bot, **text_update(user(2, "P2"), "/party"))
    again = bot.session.of_type(methods.SendMessage)[-1]
    assert again.text.startswith("Пати уже собирается") and again.reply_parameters.message_id == party_message

    feed(dispatcher, bot, **press(user(1, "P1"), party_message, party.JOIN))
    feed(dispatcher, bot, **press(user(2, "P2"), party_message, party.LEAVE))
    for number in (2, 3, 4):
        feed(dispatcher, bot, **press(user(number, f"P{number}"), party_message, party.JOIN))
    feed(dispatcher, bot, **press(user(4, "P4"), party_message, party.LEAVE))
    assert answers(bot)[:2] == ["Ты уже в пати 😉", "Тебя и так нет в пати 🤷"]
    assert "В деле 3/5" in bot.session.of_type(methods.EditMessageText)[-1].text
    assert not bot.session.of_type(methods.SendMessage)[-1].entities

    for number in (4, 5):
        feed(dispatcher, bot, **press(user(number, f"P{number}"), party_message, party.JOIN))
    edit = bot.session.of_type(methods.EditMessageText)[-1]
    assert "В деле 5/5" in edit.text and "Пати собрана" in edit.text and edit.reply_markup is None
    call = bot.session.of_type(methods.SendMessage)[-1]
    assert "пати собрана, заходим" in call.text
    assert sorted(entity.user.id for entity in call.entities) == [1, 2, 3, 4, 5]

    feed(dispatcher, bot, **press(user(6, "P6"), party_message, party.JOIN))
    assert answers(bot)[-1] == "Пати уже собрана 🎮"
    # the gathered party doesn't block a new one
    feed(dispatcher, bot, **text_update(user(6, "P6"), "/party"))
    assert "1. P6" in bot.session.of_type(methods.SendMessage)[-1].text


def test_old_party_falls_apart(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(1, "P1"), "/party"))
    party_message = bot.session.next_message_id
    db.execute("UPDATE Parties SET created_at = datetime('now', '-4 hours')")
    feed(dispatcher, bot, **press(user(2, "P2"), party_message, party.JOIN))
    assert answers(bot)[-1].startswith("Эта пати уже не работает")
    assert "Не собрались" in bot.session.of_type(methods.EditMessageText)[-1].text
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
    # CI has no .env, the token is never used by the fake session anyway
    monkeypatch.setattr(main, "get_bot_token", lambda: "42:TEST")
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "bot.db"))
    monkeypatch.setattr(main, "BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setattr(main, "MAIN_CHAT_ID", str(CHAT.id))
    monkeypatch.setattr(main, "QUOTE_OF_THE_DAY_ENABLED", True)
    try:
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(main.main())
    finally:
        for router in main.ROUTERS:
            router._parent_router = None
    assert "chat_member" in session.allowed_updates
