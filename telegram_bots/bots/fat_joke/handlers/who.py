from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyParameters

from telegram_bots.bots.fat_joke.db import who_polls as who_db
from telegram_bots.bots.fat_joke.scheduler import start_who_poll

router = Router(name="who")


@router.message(Command("who"))
async def who_command(message: Message, db):
    open_poll = who_db.get_open(db, message.chat.id)
    if open_poll:
        await message.answer(
            "Опрос уже идёт, голосуй тут 👆",
            reply_parameters=ReplyParameters(message_id=open_poll, allow_sending_without_reply=True),
        )
        return
    if not await start_who_poll(message.bot, db, message.chat.id):
        await message.answer("Для опроса нужно хотя бы двое знакомых боту людей в чате 🤷")
