import logging
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.db import weekly as weekly_db
from telegram_bots.bots.fat_joke.scheduler import KYIV
from telegram_bots.bots.fat_joke.services import achievements
from telegram_bots.bots.fat_joke.services.people import display_name, mention

logger = logging.getLogger(__name__)


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
