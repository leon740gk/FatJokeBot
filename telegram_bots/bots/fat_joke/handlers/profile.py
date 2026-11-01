from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bots.bots.fat_joke.db import achievements as achievements_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.services import achievements

router = Router(name="profile")


@router.message(Command("me"))
async def me_command(message: Message, db):
    # a reply shows the profile of whoever wrote the replied message
    replied = message.reply_to_message
    target = replied.from_user if replied and replied.from_user and not replied.from_user.is_bot else message.from_user
    users_db.register(db, target)
    iq_level, name = users_db.get_iq_and_name(db, target.id)
    text = achievements.format_profile(
        name,
        iq_level,
        achievements.battle_points(db, target.id),
        achievements.collect(db, target.id),
        achievements_db.unlocked(db, target.id),
    )
    await message.answer(text)


@router.message(Command("ranks"))
async def ranks_command(message: Message, db):
    rows = [(name, achievements.battle_points(db, user_id)) for user_id, name in users_db.get_members(db)]
    await message.answer(achievements.format_ranks(rows))
