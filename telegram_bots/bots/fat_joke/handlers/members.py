import logging

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import JOIN_TRANSITION, LEAVE_TRANSITION, ChatMemberUpdatedFilter, Command
from aiogram.types import ChatMemberUpdated, Message

from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.handlers.commands import is_chat_admin
from telegram_bots.bots.fat_joke.services.members import format_members

logger = logging.getLogger(__name__)
router = Router(name="members")
IN_CHAT_STATUSES = (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER)


def joined(db, user):
    if user.is_bot:
        return
    users_db.register(db, user)
    users_db.update_profile(db, user)
    users_db.set_in_chat(db, user.id, True)
    logger.info("user %s joined", user.id)


def left(db, user):
    users_db.set_in_chat(db, user.id, False)
    logger.info("user %s left", user.id)


# service messages "X joined" / "X left" come to every bot in the group;
# chat_member updates also come when those messages are hidden, but only to an admin bot
@router.message(F.new_chat_members)
async def new_members_message(message: Message, db):
    for user in message.new_chat_members:
        joined(db, user)


@router.message(F.left_chat_member)
async def left_member_message(message: Message, db):
    left(db, message.left_chat_member)


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def member_joined(event: ChatMemberUpdated, db):
    joined(db, event.new_chat_member.user)


@router.chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
async def member_left(event: ChatMemberUpdated, db):
    left(db, event.new_chat_member.user)


@router.message(Command("members"))
async def members_command(message: Message, db):
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("Эта команда работает только в группе 👥")
        return
    if not await is_chat_admin(message):
        await message.answer("Проверять участников могут только админы чата 😈")
        return
    present, gone = [], []
    for user_id in users_db.get_all_ids(db):
        in_chat = await check_member(message.bot, message.chat.id, user_id, db)
        users_db.set_in_chat(db, user_id, in_chat)
        (present if in_chat else gone).append(users_db.get_profile(db, user_id))
    await message.answer(format_members(present, gone))


async def check_member(bot, chat_id, user_id, db):
    """Asks Telegram whether the user is in the chat, refreshing their name and username on the way."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except TelegramBadRequest:
        # Telegram doesn't know this user in the chat at all, e.g. a deleted account
        return False
    users_db.update_profile(db, member.user)
    # a restricted (muted) member is still in the chat
    return member.status in IN_CHAT_STATUSES or getattr(member, "is_member", False)
