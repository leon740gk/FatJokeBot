from aiogram import BaseMiddleware

from telegram_bots.bots.fat_joke.db import users as users_db


class UserActivityMiddleware(BaseMiddleware):
    """Registers every new user and remembers when they were last active."""

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user and not user.is_bot:
            users_db.register(data["db"], user)
            users_db.touch_activity(data["db"], user.id)
        return await handler(event, data)
