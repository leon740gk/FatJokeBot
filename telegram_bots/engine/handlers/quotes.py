from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from telegram_bots.engine.content import kb
from telegram_bots.engine.db import quotes as quotes_db
from telegram_bots.engine.scheduler import KYIV
from telegram_bots.engine.services import quotes
from telegram_bots.engine.services.people import display_name

router = Router(name="quotes")


@router.message(Command("save"))
async def save_command(message: Message, db):
    original = message.reply_to_message
    if not original:
        await message.answer(kb.texts.save_how_to)
        return
    text = original.text or original.caption
    if not text:
        await message.answer(kb.texts.save_text_only)
        return
    author = original.from_user
    saved = quotes_db.save(
        db,
        message.chat.id,
        original.message_id,
        author.id if author else None,
        display_name(author) if author else kb.texts.unknown_author,
        author.username if author else None,
        text,
        original.date.astimezone(KYIV).date().isoformat(),
        message.from_user.id,
    )
    if not saved:
        await message.answer(kb.texts.quote_already_saved)
        return
    await message.answer(kb.texts.quote_saved.format(count=quotes_db.count(db, message.chat.id)))


@router.message(Command("quote"))
async def quote_command(message: Message, command: CommandObject, db):
    all_quotes = quotes_db.get_all(db, message.chat.id)
    if not all_quotes:
        await message.answer(kb.texts.quote_book_empty)
        return
    quote = quotes.pick(all_quotes, command.args)
    if not quote:
        await message.answer(kb.texts.quote_none_of.format(author=command.args.strip()))
        return
    await message.answer(quotes.format_quote(quote))
