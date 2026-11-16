from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from telegram_bots.engine.content import kb
from telegram_bots.engine.db import quotes as quotes_db
from telegram_bots.engine.handlers.commands import is_chat_admin
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


@router.message(Command("unquote"))
async def unquote_command(message: Message, db):
    """Takes a quote out of the book: a reply to the saved message or to a bot message showing the quote."""
    if not await is_chat_admin(message):
        await message.answer(kb.texts.unquote_admins_only)
        return
    original = message.reply_to_message
    if not original:
        await message.answer(kb.texts.unquote_how_to)
        return
    chat_id = message.chat.id
    quote = quotes.quoted_in(quotes_db.texts(db, chat_id), original.text)
    removed = quotes_db.delete_saved_from(db, chat_id, original.message_id) or (
        quote is not None and quotes_db.delete_text(db, chat_id, quote)
    )
    if not removed:
        await message.answer(kb.texts.unquote_not_found)
        return
    await message.answer(kb.texts.unquote_done.format(count=quotes_db.count(db, chat_id)))
