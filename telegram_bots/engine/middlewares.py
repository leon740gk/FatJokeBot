import logging
import time
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from telegram_bots.engine.db import users as users_db
from telegram_bots.engine.db import weekly as weekly_db
from telegram_bots.engine.scheduler import KYIV
from telegram_bots.engine.services import achievements
from telegram_bots.engine.services.people import display_name, mention

logger = logging.getLogger(__name__)


class AnonymousAdminMiddleware(BaseMiddleware):
    """Gives a message sent on behalf of the group to the admin who sent it, when that can only be one person.

    An anonymous admin writes as the group: from_user is GroupAnonymousBot and sender_chat is the chat itself.
    When exactly one admin of the chat is anonymous, the message is theirs, so it goes on as if they had written
    it themselves: their quiz, IQ, XP and activity. With several anonymous admins nothing is changed.
    """

    ADMINS_TTL = 600  # seconds the admin list is kept, admins change rarely

    def __init__(self):
        self.anonymous_admin = {}  # chat id -> (when looked up, the User or None)

    async def __call__(self, handler, event, data):
        if not isinstance(event, Message):
            return await handler(event, data)
        replied = event.reply_to_message
        if is_from_group_itself(event) or (replied and is_from_group_itself(replied)):
            admin = await self.admin_of(data["bot"], event.chat.id)
            if admin:
                event = as_admin(event, admin)
                if event.from_user == admin:
                    data["event_from_user"] = admin
        return await handler(event, data)

    async def admin_of(self, bot, chat_id):
        cached = self.anonymous_admin.get(chat_id)
        if cached and time.monotonic() - cached[0] < self.ADMINS_TTL:
            return cached[1]
        try:
            admins = await bot.get_chat_administrators(chat_id)
        except TelegramAPIError as error:
            logger.warning("can't get admins of chat %s: %s", chat_id, error.message)
            return None
        anonymous = [
            member.user
            for member in admins
            if member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR)
            and member.is_anonymous
            and not member.user.is_bot
        ]
        admin = anonymous[0] if len(anonymous) == 1 else None
        self.anonymous_admin[chat_id] = (time.monotonic(), admin)
        return admin


def is_from_group_itself(message):
    # a linked channel also has sender_chat, but it is another chat and no admin
    return bool(message.sender_chat) and message.sender_chat.id == message.chat.id


def as_admin(message, admin):
    """The message as if the anonymous admin had written it themselves, and the message it replies to too."""
    changes = {}
    if is_from_group_itself(message):
        changes = {"from_user": admin, "sender_chat": None}
    replied = message.reply_to_message
    if replied and is_from_group_itself(replied):
        changes["reply_to_message"] = replied.model_copy(update={"from_user": admin, "sender_chat": None})
    return message.model_copy(update=changes)


class UserActivityMiddleware(BaseMiddleware):
    """Registers every new user, remembers when they were last active and hands out achievements."""

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if not user or user.is_bot:
            return await handler(event, data)
        db = data["db"]
        users_db.register(db, user)
        users_db.touch_activity(db, user.id)
        chat = data.get("event_chat")
        in_group = chat and chat.type != ChatType.PRIVATE
        if in_group:
            # writing in the group means they are in it, e.g. came back after leaving
            users_db.set_in_chat(db, user.id, True)
            if isinstance(event, Message):
                weekly_db.count_message(db, chat.id, user.id, datetime.now(KYIV).date().isoformat())
        result = await handler(event, data)
        if in_group:
            # after the handler, so the answer that earned it comes first
            await announce_achievements(data["bot"], db, chat.id, user)
        return result


async def announce_achievements(bot, db, chat_id, user):
    # the rank-up from the loot itself is shown on the loot message, here only the one from the achievements
    old_points = achievements.battle_points(db, user.id)
    codes = achievements.unlock_new(db, user.id, datetime.now(KYIV))
    if not codes:
        return
    who = mention(display_name(user), user.username)
    text = achievements.announcement(who, codes, old_points, achievements.battle_points(db, user.id))
    try:
        await bot.send_message(chat_id, text)
    except TelegramAPIError as error:
        logger.warning("can't announce achievements in chat %s: %s", chat_id, error.message)
