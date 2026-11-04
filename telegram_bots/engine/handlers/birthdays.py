from datetime import datetime

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from telegram_bots.engine.content import kb
from telegram_bots.engine.db import users as users_db
from telegram_bots.engine.handlers.commands import is_chat_admin
from telegram_bots.engine.scheduler import KYIV
from telegram_bots.engine.services import birthdays
from telegram_bots.engine.services.people import display_name

router = Router(name="birthdays")
# "/birthday -" forgets the saved birthday
FORGET = "-"


@router.message(Command("birthday"))
async def birthday_command(message: Message, command: CommandObject, db):
    """/birthday 03.05[.1990] for yourself; an admin replies with it to set someone else's."""
    replied = message.reply_to_message
    target = message.from_user
    if replied and replied.from_user and not replied.from_user.is_bot and replied.from_user.id != target.id:
        if not await is_chat_admin(message):
            await message.answer(kb.texts.birthday_admins_only)
            return
        target = replied.from_user
        users_db.register(db, target)
    name = display_name(target)
    args = (command.args or "").strip()

    if not args:
        stored = users_db.get_birthday(db, target.id)
        known = birthdays.parse(stored) if stored else None
        text = kb.texts.birthday_known.format(name=name, date=known.stored()) if known else kb.texts.birthday_unknown
        await message.answer(text + "\n\n" + kb.texts.birthday_how_to)
        return
    if args == FORGET:
        users_db.set_birthday(db, target.id, None)
        await message.answer(kb.texts.birthday_forgotten.format(name=name))
        return
    birthday = birthdays.parse(args, datetime.now(KYIV).date())
    if not birthday:
        await message.answer(kb.texts.birthday_bad_date + "\n\n" + kb.texts.birthday_how_to)
        return
    users_db.set_birthday(db, target.id, birthday.stored())
    await message.answer(kb.texts.birthday_saved.format(name=name, date=birthday.stored()))


@router.message(Command("birthdays"))
async def birthdays_command(message: Message, db):
    today = datetime.now(KYIV).date()
    await message.answer(birthdays.format_upcoming(users_db.get_birthdays(db), today))
