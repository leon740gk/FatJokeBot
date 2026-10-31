import contextlib

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message, ReplyParameters
from aiogram.utils.keyboard import InlineKeyboardBuilder

from telegram_bots.bots.fat_joke.db import parties as parties_db
from telegram_bots.bots.fat_joke.services import party
from telegram_bots.bots.fat_joke.services.people import display_name

router = Router(name="party")
DEAD_PARTY = "Эта пати уже не работает, собери новую: /party"


def party_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Я в деле", callback_data=party.JOIN)
    keyboard.button(text="❌ Выхожу", callback_data=party.LEAVE)
    return keyboard.as_markup()


@router.message(Command("party"))
async def party_command(message: Message, command: CommandObject, db):
    chat_id = message.chat.id
    open_message_id = parties_db.get_open(db, chat_id, party.PARTY_HOURS)
    if open_message_id:
        await message.answer(
            "Пати уже собирается, жми кнопку тут 👆",
            reply_parameters=ReplyParameters(message_id=open_message_id, allow_sending_without_reply=True),
        )
        return
    comment = (command.args or "").strip()
    user = message.from_user
    creator = (user.id, display_name(user), user.username)
    sent = await message.answer(party.party_text(comment, [creator]), reply_markup=party_keyboard())
    party_id = parties_db.create(db, chat_id, sent.message_id, user.id, comment)
    parties_db.join(db, party_id, *creator)


@router.callback_query(F.data.in_({party.JOIN, party.LEAVE}))
async def party_callback(callback: CallbackQuery, db):
    message = callback.message
    found = isinstance(message, Message) and parties_db.find(db, message.chat.id, message.message_id, party.PARTY_HOURS)
    if not found:
        await callback.answer(DEAD_PARTY, show_alert=True)
        return
    party_id, comment, is_gathered, is_expired = found
    if is_gathered:
        await callback.answer("Пати уже собрана 🎮")
        return
    if is_expired:
        await callback.answer(DEAD_PARTY, show_alert=True)
        with contextlib.suppress(TelegramBadRequest):
            await message.edit_text(party.party_text(comment, parties_db.members(db, party_id), expired=True))
        return

    user = callback.from_user
    if callback.data == party.JOIN:
        if not parties_db.join(db, party_id, user.id, display_name(user), user.username):
            await callback.answer("Ты уже в пати 😉")
            return
        await callback.answer("Ты в деле! 🎮")
    else:
        if not parties_db.leave(db, party_id, user.id):
            await callback.answer("Тебя и так нет в пати 🤷")
            return
        await callback.answer("Ты вышел из пати")

    members = parties_db.members(db, party_id)
    gathered = len(members) >= party.PARTY_SIZE and parties_db.mark_gathered(db, party_id)
    await message.edit_text(party.party_text(comment, members), reply_markup=None if gathered else party_keyboard())
    if gathered:
        await message.answer(**party.gathered_call(members).as_kwargs())
