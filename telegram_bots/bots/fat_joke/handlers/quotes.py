from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from telegram_bots.bots.fat_joke.db import quotes as quotes_db
from telegram_bots.bots.fat_joke.scheduler import KYIV
from telegram_bots.bots.fat_joke.services import quotes
from telegram_bots.bots.fat_joke.services.people import display_name

router = Router(name="quotes")
EMPTY_BOOK = "Цитатник пока пуст 📭\nОтветь командой /save на смешное сообщение, и оно попадёт сюда."


@router.message(Command("save"))
async def save_command(message: Message, db):
    original = message.reply_to_message
    if not original:
        await message.answer("Ответь командой /save на сообщение, которое надо увековечить 📜")
        return
    text = original.text or original.caption
    if not text:
        await message.answer("В цитатник попадает только текст 🤷")
        return
    author = original.from_user
    saved = quotes_db.save(
        db,
        message.chat.id,
        original.message_id,
        author.id if author else None,
        display_name(author) if author else "Неизвестный гений",
        author.username if author else None,
        text,
        original.date.astimezone(KYIV).date().isoformat(),
        message.from_user.id,
    )
    if not saved:
        await message.answer("Эта цитата уже в цитатнике 📜")
        return
    await message.answer(f"Сохранено в цитатник 📜 Всего цитат: {quotes_db.count(db, message.chat.id)}")


@router.message(Command("quote"))
async def quote_command(message: Message, command: CommandObject, db):
    all_quotes = quotes_db.get_all(db, message.chat.id)
    if not all_quotes:
        await message.answer(EMPTY_BOOK)
        return
    quote = quotes.pick(all_quotes, command.args)
    if not quote:
        await message.answer(f"У «{command.args.strip()}» цитат пока нет 🤔")
        return
    await message.answer(quotes.format_quote(quote))
