import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from telegram_bots.bots.fat_joke.db import quiz as quiz_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.services import quiz, texts
from telegram_bots.knowledge_base.fat_joke.reaction_data import wanted

logger = logging.getLogger(__name__)
KYIV = ZoneInfo("Europe/Kyiv")


async def hourly_bam(bot, chat_id):
    await bot.send_message(chat_id, texts.hour_message(datetime.now(KYIV).strftime("%H")))


async def send_quiz_question(bot, db, chat_id):
    question = quiz.pick_question()
    keyboard = InlineKeyboardBuilder()
    for option_index, (label, _) in enumerate(question.options):
        keyboard.button(text=label, callback_data=quiz.option_callback_data(question, option_index))
    keyboard.adjust(2)
    message = await bot.send_message(chat_id, quiz.question_message_text(question), reply_markup=keyboard.as_markup())
    quiz_db.save_quiz_message(db, message.chat.id, message.message_id, question.discipline, question.number)


async def update_activity(db):
    users_db.update_activity_deltas(db)


async def we_miss_you(bot, db, chat_id):
    message = texts.miss_you_message(users_db.get_inactive(db))
    if message:
        await bot.send_message(chat_id, message)
        await bot.send_sticker(chat_id, wanted)


def create_scheduler(bot, db, chat_id, miss_you_enabled=False):
    scheduler = AsyncIOScheduler(timezone=KYIV)
    scheduler.add_job(update_activity, "cron", hour=14, minute=55, kwargs={"db": db})
    if not chat_id:
        logger.warning("FAT_JOKE_MAIN_CHAT_ID is not set, chat messages on a schedule are off")
        return scheduler

    scheduler.add_job(hourly_bam, "cron", minute=0, kwargs={"bot": bot, "chat_id": chat_id})
    scheduler.add_job(send_quiz_question, "interval", minutes=20, kwargs={"bot": bot, "db": db, "chat_id": chat_id})
    if miss_you_enabled:
        scheduler.add_job(we_miss_you, "cron", hour=15, minute=0, kwargs={"bot": bot, "db": db, "chat_id": chat_id})
    return scheduler
