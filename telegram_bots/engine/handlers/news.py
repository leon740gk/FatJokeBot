from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bots.engine.content import kb
from telegram_bots.engine.scheduler import post_news

router = Router(name="news")


@router.message(Command("news"))
async def news_command(message: Message, db):
    """The fresh news right now; what it posts won't come again in the morning digest."""
    if not kb.news_data.feeds:
        await message.answer(kb.texts.news_off)
        return
    if not await post_news(message.bot, db, message.chat.id):
        await message.answer(kb.texts.news_empty)
