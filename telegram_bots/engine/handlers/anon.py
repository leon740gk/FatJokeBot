import logging
from datetime import datetime

from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from telegram_bots.engine.content import kb
from telegram_bots.engine.db import chat_games as games_db
from telegram_bots.engine.handlers.members import IN_CHAT_STATUSES
from telegram_bots.engine.scheduler import KYIV
from telegram_bots.engine.services import chat_games

logger = logging.getLogger(__name__)
router = Router(name="anon")


async def is_member(bot, chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except TelegramAPIError:
        return False
    # a muted member is still in the chat
    return member.status in IN_CHAT_STATUSES or (
        member.status == ChatMemberStatus.RESTRICTED and getattr(member, "is_member", False)
    )


def how_to():
    return kb.texts.anon_how_to.format(limit=chat_games.ANON_DAILY_LIMIT)


@router.message(CommandStart())
async def start_command(message: Message, settings):
    # /start is what a person presses first in a private chat with the bot
    if message.chat.type != ChatType.PRIVATE:
        return
    text = kb.reaction_data.commands_responses["help"]
    if settings.anon_enabled and settings.main_chat_id:
        text = how_to() + "\n" + text
    await message.answer(text)


@router.message(Command("anon"))
async def anon_command(message: Message, command: CommandObject, db, settings):
    if not settings.anon_enabled or not settings.main_chat_id:
        await message.answer(kb.texts.anon_off)
        return
    if message.chat.type != ChatType.PRIVATE:
        # the name is right there on the command, take it away as fast as possible
        try:
            await message.delete()
        except TelegramAPIError as error:
            logger.debug("can't delete /anon in chat %s: %s", message.chat.id, error.message)
        username = (await message.bot.me()).username
        await message.answer(kb.texts.anon_in_private.format(link=f"https://t.me/{username}"))
        return

    text = (command.args or "").strip()
    if not text:
        await message.answer(how_to())
        return
    if len(text) > chat_games.ANON_MAX_LENGTH:
        await message.answer(kb.texts.anon_too_long.format(limit=chat_games.ANON_MAX_LENGTH))
        return
    user_id = message.from_user.id
    if not await is_member(message.bot, settings.main_chat_id, user_id):
        await message.answer(kb.texts.anon_not_member)
        return
    day = datetime.now(KYIV).date().isoformat()
    if games_db.anon_sent_on(db, user_id, day) >= chat_games.ANON_DAILY_LIMIT:
        await message.answer(kb.texts.anon_limit.format(limit=chat_games.ANON_DAILY_LIMIT))
        return
    try:
        sent = await message.bot.send_message(settings.main_chat_id, kb.texts.anon_post.format(text=text))
    except TelegramAPIError as error:
        logger.error("can't post an anonymous message to chat %s: %s", settings.main_chat_id, error.message)
        await message.answer(kb.texts.anon_off)
        return
    games_db.save_anon(db, user_id, day, int(settings.main_chat_id), sent.message_id)
    await message.answer(kb.texts.anon_sent)
