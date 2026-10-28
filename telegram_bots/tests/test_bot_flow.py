"""Feeds real Telegram updates through the aiogram dispatcher, with a fake session instead of the network."""

import asyncio
from datetime import datetime

import pytest
from aiogram import Bot, methods
from aiogram.client.session.base import BaseSession
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from telegram_bots.bots.fat_joke import main
from telegram_bots.bots.fat_joke.db import quiz as quiz_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.handlers import commands, reactions
from telegram_bots.bots.fat_joke.handlers import quiz as quiz_handlers
from telegram_bots.bots.fat_joke.scheduler import create_scheduler, send_quiz_question
from telegram_bots.bots.fat_joke.services import quiz
from telegram_bots.knowledge_base.fat_joke.reaction_data import red_blink

CHAT = Chat(id=-100500, type="supergroup", title="Test chat")
BOT_USER = User(id=42, is_bot=True, first_name="FatJoke", username="fat_joke_bot")


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.requests = []
        self.next_message_id = 1000

    async def make_request(self, bot, method, timeout=None):
        self.requests.append(method)
        if isinstance(method, methods.GetMe):
            return BOT_USER
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


@pytest.fixture
def bot():
    return Bot("42:TEST", session=FakeSession())


@pytest.fixture
def dispatcher(db):
    yield main.build_dispatcher(db)
    # module level routers can belong to one dispatcher only, detach them for the next test
    for router in (commands.router, quiz_handlers.router, reactions.router):
        router._parent_router = None


def user(user_id, name):
    return User(id=user_id, is_bot=False, first_name=name, username=name.lower())


def feed(dispatcher, bot, **update):
    asyncio.run(dispatcher.feed_update(bot, Update(update_id=1, **update)))


def text_update(from_user, text, message_id=1):
    return {"message": Message(message_id=message_id, date=datetime.now(), chat=CHAT, from_user=from_user, text=text)}


def press(from_user, message_id, data):
    message = Message(message_id=message_id, date=datetime.now(), chat=CHAT, from_user=BOT_USER, text="?")
    return {"callback_query": CallbackQuery(id="1", from_user=from_user, chat_instance="c", message=message, data=data)}


def test_help_command_replies_and_registers_user(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Newbie"), "/help@fat_joke_bot"))
    sent = bot.session.of_type(methods.SendMessage)
    assert len(sent) == 1 and "/show_iq" in sent[0].text
    assert users_db.get_iq_and_name(db, 7) == (100, "Newbie")


def test_text_keywords_reply_once_per_group(db, bot, dispatcher, monkeypatch):
    monkeypatch.setattr("telegram_bots.bots.fat_joke.services.reactions.PHILOSOPHY_CHANCE", 0)
    feed(dispatcher, bot, **text_update(user(7, "Newbie"), "Сергій, серега, слава україні"))
    texts = [request.text for request in bot.session.of_type(methods.SendMessage)]
    assert len(texts) == 2 and "Героям Слава!!!" in texts
    assert len(bot.session.of_type(methods.SendSticker)) == 1


def test_quiz_round(db, bot, dispatcher):
    users_db.register(db, user(7, "Alex"))
    users_db.register(db, user(8, "Bob"))
    asyncio.run(send_quiz_question(bot, db, CHAT.id))
    question_message = bot.session.of_type(methods.SendMessage)[0]
    buttons = [button for row in question_message.reply_markup.inline_keyboard for button in row]
    assert len(buttons) == 4 and len(question_message.reply_markup.inline_keyboard) == 2

    parsed = quiz.parse_callback(buttons[0].callback_data)
    is_correct = quiz.get_question(parsed.discipline, parsed.number).options[0][1]
    message_id = bot.session.next_message_id

    feed(dispatcher, bot, **press(user(7, "Alex"), message_id, buttons[0].callback_data))
    assert bot.session.of_type(methods.EditMessageText)
    assert users_db.get_iq_and_name(db, 7)[0] == (101 if is_correct else 99)

    # Bob presses a button on the same message a moment later: nothing is counted
    feed(dispatcher, bot, **press(user(8, "Bob"), message_id, buttons[1].callback_data))
    assert bot.session.of_type(methods.AnswerCallbackQuery)[-1].text == "Це питання вже закрите"
    assert users_db.get_iq_and_name(db, 8)[0] == 100

    # the same question asked again later: Alex is caught cheating
    quiz_db.save_quiz_message(db, CHAT.id, 5000, parsed.discipline, parsed.number)
    feed(dispatcher, bot, **press(user(7, "Alex"), 5000, buttons[1].callback_data))
    assert bot.session.of_type(methods.SendAnimation)[-1].animation == red_blink
    assert "Чітер в чаті" in bot.session.of_type(methods.EditMessageText)[-1].text


def test_old_buttons_are_closed(db, bot, dispatcher):
    feed(dispatcher, bot, **press(user(7, "Alex"), 1, "correct 5"))
    assert bot.session.of_type(methods.AnswerCallbackQuery)[-1].text == "Це питання вже закрите"
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
    async def job_ids(chat_id, miss_you):
        return sorted(job.func.__name__ for job in create_scheduler(bot, db, chat_id, miss_you).get_jobs())

    assert asyncio.run(job_ids("", False)) == ["update_activity"]
    assert asyncio.run(job_ids(CHAT.id, False)) == ["hourly_bam", "send_quiz_question", "update_activity"]
    assert "we_miss_you" in asyncio.run(job_ids(CHAT.id, True))
