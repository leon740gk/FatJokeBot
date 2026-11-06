"""A Telegram stand-in for the flow tests: real updates go through the dispatcher, nothing reaches the network."""

import asyncio
from datetime import datetime

from aiogram import methods
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    Chat,
    ChatMemberLeft,
    ChatMemberMember,
    ChatMemberOwner,
    ChatMemberRestricted,
    Message,
    PhotoSize,
    Poll,
    PollOption,
    Update,
    User,
)

from telegram_bots.engine.services import loot

CHAT = Chat(id=-100500, type="supergroup", title="Test chat")
BOT_USER = User(id=42, is_bot=True, first_name="FatJoke", username="fat_joke_bot")


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.requests = []
        self.next_message_id = 1000
        self.admins = set()
        self.anonymous_admins = []  # (id, name) of admins who write as the group, for GetChatAdministrators
        self.missing_chats = set()
        self.left_chats = set()
        self.left_users = set()
        self.muted_users = set()
        self.unknown_users = set()
        self.poll_votes = []  # voter counts StopPoll returns, by option

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
        if isinstance(method, methods.GetChatAdministrators):
            owner = ChatMemberOwner(user=User(id=1, is_bot=False, first_name="Owner"), is_anonymous=False)
            anonymous = [
                ChatMemberOwner(user=User(id=user_id, is_bot=False, first_name=name), is_anonymous=True)
                for user_id, name in self.anonymous_admins
            ]
            return [owner, *anonymous]
        if isinstance(method, methods.StopPoll):
            options = [
                PollOption(persistent_id=str(i), text=str(i), voter_count=n) for i, n in enumerate(self.poll_votes)
            ]
            return Poll(
                id="1",
                question="?",
                options=options,
                total_voter_count=sum(self.poll_votes),
                is_closed=True,
                is_anonymous=False,
                type="regular",
                allows_multiple_answers=False,
                allows_revoting=True,
                members_only=False,
            )
        sent_types = (
            methods.SendMessage,
            methods.SendSticker,
            methods.SendAnimation,
            methods.SendPhoto,
            methods.SendPoll,
        )
        if isinstance(method, sent_types):
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


def press(from_user, message_id, data, photo=False):
    content = {"photo": [PhotoSize(file_id="p", file_unique_id="p", width=1, height=1)], "caption": "?"}
    message = Message(
        message_id=message_id,
        date=datetime.now(),
        chat=CHAT,
        from_user=BOT_USER,
        **(content if photo else {"text": "?"}),
    )
    return {"callback_query": CallbackQuery(id="1", from_user=from_user, chat_instance="c", message=message, data=data)}


def sent_texts(bot):
    return [request.text for request in bot.session.of_type(methods.SendMessage)]


def sent_question(bot):
    message = bot.session.of_type(methods.SendMessage)[-1]
    buttons = [button for row in message.reply_markup.inline_keyboard for button in row]
    return message, buttons


class LootRandom:
    """Always spawns the given objective."""

    def __init__(self, code):
        self.code = code

    def random(self):
        return 0

    def choices(self, kinds, weights):
        return [loot.kinds()[self.code]]

    def choice(self, items):
        return list(items)[0]


def press_loot(dispatcher, bot, from_user, message_id, text):
    message = Message(message_id=message_id, date=datetime.now(), chat=CHAT, from_user=BOT_USER, text=text)
    query = CallbackQuery(id="1", from_user=from_user, chat_instance="c", message=message, data=loot.CALLBACK)
    feed(dispatcher, bot, callback_query=query)
