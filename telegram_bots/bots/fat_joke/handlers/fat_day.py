import asyncio
import random
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bots.bots.fat_joke.db import fat_days as fat_days_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.scheduler import KYIV
from telegram_bots.bots.fat_joke.services import fat_day

router = Router(name="fat_day")
# only people who wrote in the last month can become the fatty, so the long gone don't win
ACTIVE_DAYS = 30
SCAN_PAUSE_SECONDS = 1.5


@router.message(Command("fat"))
async def fat_command(message: Message, db):
    chat_id = message.chat.id
    day = datetime.now(KYIV).date().isoformat()
    winner = fat_days_db.get_winner(db, chat_id, day)
    if winner:
        await message.answer(fat_day.already_picked(winner))
        return
    # never empty: the activity middleware has just touched the one who sent /fat
    candidates = users_db.get_active_since(db, datetime.now() - timedelta(days=ACTIVE_DAYS))
    user_id, name, username = random.choice(candidates)
    if not fat_days_db.claim(db, chat_id, day, user_id):
        await message.answer(fat_day.already_picked(fat_days_db.get_winner(db, chat_id, day)))
        return
    steps = fat_day.scan_messages((name, username))
    for step in steps[:-1]:
        await message.answer(step)
        await asyncio.sleep(SCAN_PAUSE_SECONDS)
    await message.answer(steps[-1])


@router.message(Command("fatstats"))
async def fat_stats_command(message: Message, db):
    await message.answer(fat_day.format_stats(fat_days_db.get_stats(db, message.chat.id)))
