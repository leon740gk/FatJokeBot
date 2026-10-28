import functools
import logging
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from telegram_bots.bots.fat_joke.db import quiz as quiz_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.db.backup import backup_database
from telegram_bots.bots.fat_joke.services import quiz, texts
from telegram_bots.bots.fat_joke.services.quiet_hours import is_quiet
from telegram_bots.knowledge_base.fat_joke.reaction_data import wanted

logger = logging.getLogger(__name__)
KYIV = ZoneInfo("Europe/Kyiv")
NOT_IN_CHAT_HINT = "is the bot a member of this chat? Check FAT_JOKE_MAIN_CHAT_ID, /chat_id shows the id of any chat"


def chat_job(job):
    """Turns Telegram errors of a scheduled chat message into one readable log line instead of a traceback."""

    @functools.wraps(job)
    async def wrapper(*args, **kwargs):
        try:
            return await job(*args, **kwargs)
        except TelegramAPIError as error:
            logger.error(
                "%s: can't send to chat %s: %s (%s)",
                job.__name__,
                kwargs.get("chat_id"),
                error.message,
                NOT_IN_CHAT_HINT,
            )

    return wrapper


async def check_chat(bot, chat_id):
    """Logs an error at start if the bot can't write to the main chat."""
    try:
        member = await bot.get_chat_member(chat_id, bot.id)
    except TelegramAPIError as error:
        logger.error("main chat %s: %s (%s)", chat_id, error.message, NOT_IN_CHAT_HINT)
        return False
    if member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
        status = "been kicked from" if member.status == ChatMemberStatus.KICKED else "left"
        logger.error("main chat %s: the bot has %s it (%s)", chat_id, status, NOT_IN_CHAT_HINT)
        return False
    return True


@chat_job
async def hourly_bam(bot, chat_id):
    await bot.send_message(chat_id, texts.hour_message(datetime.now(KYIV).strftime("%H")))


def build_keyboard(rendered):
    keyboard = InlineKeyboardBuilder()
    for row in rendered.rows:
        for label, data in row:
            keyboard.button(text=label, callback_data=data)
    keyboard.adjust(*(len(row) for row in rendered.rows))
    return keyboard.as_markup()


async def ask_question(bot, db, chat_id, discipline=None, into_message_id=None, rng=random):
    """Sends a quiz question, of the current discipline unless another one is given.

    into_message_id turns an existing message (the topic picker) into the question instead of sending a new one.
    When a season runs out of questions, the winners are announced first.
    """
    discipline = discipline or quiz.current_discipline(db)
    picked = quiz.pick_question(db, discipline, rng)
    if picked.finished_season:
        await bot.send_message(chat_id, quiz.format_season_end(discipline, picked.finished_season, picked.winners))

    rendered = quiz.render_question(picked.question, rng)
    if into_message_id:
        await bot.edit_message_text(
            rendered.text, chat_id=chat_id, message_id=into_message_id, reply_markup=build_keyboard(rendered)
        )
        message_id = into_message_id
    else:
        message_id = (await bot.send_message(chat_id, rendered.text, reply_markup=build_keyboard(rendered))).message_id
    quiz_db.save_quiz_message(db, chat_id, message_id, discipline, picked.season, picked.question.number)


@chat_job
async def scheduled_question(bot, db, chat_id, quiet_hours=None):
    if is_quiet(datetime.now(KYIV).hour, quiet_hours):
        return
    discipline = quiz.current_discipline(db)
    if quiz_db.get_open_question(db, chat_id, discipline):
        # the previous question of this discipline is still open, don't pile them up
        return
    await ask_question(bot, db, chat_id, discipline)


async def close_expired_questions(bot, db, minutes):
    for chat_id, message_id, discipline, number in quiz_db.close_expired(db, minutes):
        question = quiz.get_question(discipline, number)
        if not question:
            continue
        try:
            await bot.edit_message_text(quiz.expired_text(question), chat_id=chat_id, message_id=message_id)
        except TelegramAPIError as error:
            logger.warning("can't close expired question %s in chat %s: %s", message_id, chat_id, error)


async def update_activity(db):
    users_db.update_activity_deltas(db)


@chat_job
async def we_miss_you(bot, db, chat_id):
    message = texts.miss_you_message(users_db.get_inactive(db))
    if message:
        await bot.send_message(chat_id, message)
        await bot.send_sticker(chat_id, wanted)


async def backup(db_path, backup_dir):
    backup_database(db_path, backup_dir)


def create_scheduler(
    bot,
    db,
    chat_id,
    miss_you_enabled=False,
    db_path=None,
    backup_dir=None,
    answer_minutes=15,
    quiet_hours=None,
):
    scheduler = AsyncIOScheduler(timezone=KYIV)
    scheduler.add_job(update_activity, "cron", hour=14, minute=55, kwargs={"db": db})
    scheduler.add_job(
        close_expired_questions, "interval", minutes=1, kwargs={"bot": bot, "db": db, "minutes": answer_minutes}
    )
    if db_path and backup_dir:
        # the laptop may sleep at 04:00, so a missed backup still runs when it wakes up the same day
        scheduler.add_job(
            backup,
            "cron",
            hour=4,
            minute=0,
            misfire_grace_time=20 * 60 * 60,
            coalesce=True,
            kwargs={"db_path": db_path, "backup_dir": backup_dir},
        )
    if not chat_id:
        logger.warning("FAT_JOKE_MAIN_CHAT_ID is not set, chat messages on a schedule are off")
        return scheduler

    scheduler.add_job(hourly_bam, "cron", minute=0, kwargs={"bot": bot, "chat_id": chat_id})
    scheduler.add_job(
        scheduled_question,
        "interval",
        minutes=20,
        kwargs={"bot": bot, "db": db, "chat_id": chat_id, "quiet_hours": quiet_hours},
    )
    if miss_you_enabled:
        scheduler.add_job(we_miss_you, "cron", hour=15, minute=0, kwargs={"bot": bot, "db": db, "chat_id": chat_id})
    return scheduler
