from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyParameters

from telegram_bots.engine.content import kb
from telegram_bots.engine.db import who_polls as who_db
from telegram_bots.engine.scheduler import start_who_poll

router = Router(name="who")


@router.message(Command("who"))
async def who_command(message: Message, db):
    open_poll = who_db.get_open(db, message.chat.id)
    if open_poll:
        await message.answer(
            kb.texts.who_already_open,
            reply_parameters=ReplyParameters(message_id=open_poll, allow_sending_without_reply=True),
        )
        return
    if not await start_who_poll(message.bot, db, message.chat.id):
        await message.answer(kb.texts.who_not_enough)
