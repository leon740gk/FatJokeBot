import functools
import logging
import random
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ReplyParameters
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from telegram_bots.config import env_prefix
from telegram_bots.engine import content
from telegram_bots.engine.content import kb
from telegram_bots.engine.db import bets as bets_db
from telegram_bots.engine.db import duels as duels_db
from telegram_bots.engine.db import loot as loot_db
from telegram_bots.engine.db import quiz as quiz_db
from telegram_bots.engine.db import quotes as quotes_db
from telegram_bots.engine.db import users as users_db
from telegram_bots.engine.db import who_polls as who_db
from telegram_bots.engine.db.backup import backup_database
from telegram_bots.engine.services import bets, duel, loot, quiz, quotes, texts, weekly, who
from telegram_bots.engine.services.people import mention
from telegram_bots.engine.services.quiet_hours import is_quiet

logger = logging.getLogger(__name__)
KYIV = ZoneInfo("Europe/Kyiv")


def not_in_chat_hint():
    return (
        f"is the bot a member of this chat? Check {env_prefix(content.active())}_MAIN_CHAT_ID, "
        "/chat_id shows the id of any chat"
    )


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
                not_in_chat_hint(),
            )

    return wrapper


async def check_chat(bot, chat_id):
    """Logs an error at start if the bot can't write to the main chat."""
    try:
        member = await bot.get_chat_member(chat_id, bot.id)
    except TelegramAPIError as error:
        logger.error("main chat %s: %s (%s)", chat_id, error.message, not_in_chat_hint())
        return False
    if member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
        status = "been kicked from" if member.status == ChatMemberStatus.KICKED else "left"
        logger.error("main chat %s: the bot has %s it (%s)", chat_id, status, not_in_chat_hint())
        return False
    return True


@chat_job
async def hourly_bam(bot, db, chat_id, quiet_hours=None, rng=random):
    """The time message; in the daytime now and then with an MLBB objective for the fastest to take."""
    now = datetime.now(KYIV)
    text = texts.hour_message(now)
    kind = None if is_quiet(now.hour, quiet_hours) else loot.roll(rng)
    if not kind:
        await bot.send_message(chat_id, text)
        return
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text=kb.theme_data.loot_button, callback_data=loot.CALLBACK)
    sent = await bot.send_message(chat_id, loot.spawn_text(text, kind), reply_markup=keyboard.as_markup())
    loot_db.create(db, int(chat_id), sent.message_id, kind.code, kind.points)


def build_keyboard(rendered):
    keyboard = InlineKeyboardBuilder()
    for row in rendered.rows:
        for label, data in row:
            keyboard.button(text=label, callback_data=data)
    keyboard.adjust(*(len(row) for row in rendered.rows))
    return keyboard.as_markup()


async def ask_question(bot, db, chat_id, discipline=None, into_message_id=None, asked_by=None, rng=random):
    """Sends a quiz question, of the current discipline unless another one is given.

    into_message_id turns an existing message (the topic picker) into the question instead of sending a new one.
    asked_by is who called it, only they can answer; scheduled questions are for everyone.
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
    quiz_db.save_quiz_message(db, chat_id, message_id, discipline, picked.season, picked.question.number, asked_by)


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
        if kb.reaction_data.wanted:
            await bot.send_sticker(chat_id, kb.reaction_data.wanted)


@chat_job
async def quote_of_the_day(bot, db, chat_id):
    quote = quotes_db.take_least_shown(db, int(chat_id))
    if quote:
        await bot.send_message(chat_id, quotes.format_quote(quote, title=kb.texts.quote_of_the_day))


@chat_job
async def weekly_summary(bot, db, chat_id):
    week = weekly.collect(db, int(chat_id), datetime.now(KYIV).date())
    await bot.send_message(chat_id, weekly.format_week(week))


async def start_who_poll(bot, db, chat_id, rng=random):
    """Sends a "Кто из нас…" poll with the chat members; returns its message_id, None with fewer than two people."""
    options = who.pick_options(users_db.get_member_profiles(db), rng)
    if not options:
        return None
    question = who.pick_question(who_db.used_questions(db, int(chat_id)), rng)
    sent = await bot.send_poll(chat_id, question, options=who.option_labels(options), is_anonymous=False)
    who_db.create(db, int(chat_id), sent.message_id, question, options)
    return sent.message_id


@chat_job
async def who_poll(bot, db, chat_id):
    if not who_db.get_open(db, int(chat_id)):
        await start_who_poll(bot, db, chat_id)


async def close_who_polls(bot, db, hours=who.POLL_HOURS):
    for chat_id, message_id, question, options in who_db.take_expired(db, hours):
        try:
            poll = await bot.stop_poll(chat_id, message_id)
            text = who.result(question, options, [option.voter_count for option in poll.options])
            await bot.send_message(
                chat_id,
                **text.as_kwargs(),
                reply_parameters=ReplyParameters(message_id=message_id, allow_sending_without_reply=True),
            )
        except TelegramAPIError as error:
            logger.warning("can't close the who poll %s in chat %s: %s", message_id, chat_id, error.message)


def duelist_names(db, current):
    names = {}
    for user_id in (current.challenger, current.opponent):
        profile = users_db.get_profile(db, user_id)
        names[user_id] = mention(profile[1], profile[2]) if profile else str(user_id)
    return names


def settle_bets(db, current, winner):
    """Pays the bets out (or back) and returns the lines about them for the duel message."""
    placed = bets_db.for_duel(db, current.id)
    paid = bets.payouts(placed, winner)
    bets_db.settle(db, current.id, paid)
    names = {}
    for user_id, _, _ in placed:
        profile = users_db.get_profile(db, user_id)
        names[user_id] = profile[1] if profile else str(user_id)
    return bets.settle_lines(placed, paid, names)


async def finish_duel(bot, db, current):
    """Picks the winner once both have answered or the time is up, and shows the result on the duel message."""
    question = quiz.get_question(current.discipline, current.question_number)
    winner = duel.winner_of(current, question) if question else None
    if not duels_db.finish(db, current.id, winner, duel.PRIZE if winner else 0):
        return
    bet_lines = settle_bets(db, current, winner)
    if not question:
        return
    text = "\n".join([duel.result_text(current, question, duelist_names(db, current), winner), *bet_lines])
    try:
        await bot.edit_message_text(text, chat_id=current.chat_id, message_id=current.message_id)
    except TelegramAPIError as error:
        logger.warning("can't show the duel %s result: %s", current.id, error.message)


async def close_duels(bot, db):
    pending, active = duels_db.stale(db, duel.ACCEPT_MINUTES, time.time() - duel.ANSWER_SECONDS)
    for row in pending:
        current = duel.from_row(row)
        if duels_db.set_status(db, current.id, "pending", "expired") and current.message_id:
            names = duelist_names(db, current)
            refunded = kb.texts.bets_refunded if settle_bets(db, current, None) else ""
            try:
                await bot.edit_message_text(
                    kb.texts.duel_expired.format(opponent=names[current.opponent], challenger=names[current.challenger])
                    + refunded,
                    chat_id=current.chat_id,
                    message_id=current.message_id,
                )
            except TelegramAPIError as error:
                logger.warning("can't close the duel %s: %s", current.id, error.message)
    for row in active:
        await finish_duel(bot, db, duel.from_row(row))


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
    quiz_schedule_enabled=False,
    quiet_hours=None,
    quote_of_the_day_enabled=False,
    weekly_summary_enabled=False,
    who_poll_enabled=False,
):
    scheduler = AsyncIOScheduler(timezone=KYIV)
    scheduler.add_job(update_activity, "cron", hour=14, minute=55, kwargs={"db": db})
    scheduler.add_job(
        close_expired_questions, "interval", minutes=1, kwargs={"bot": bot, "db": db, "minutes": answer_minutes}
    )
    scheduler.add_job(close_who_polls, "interval", minutes=1, kwargs={"bot": bot, "db": db})
    scheduler.add_job(close_duels, "interval", minutes=1, kwargs={"bot": bot, "db": db})
    if db_path and backup_dir:
        # the bot may be down at 04:00 (laptop asleep, restart), so a missed backup still runs later the same day
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
        logger.warning("%s_MAIN_CHAT_ID is not set, chat messages on a schedule are off", env_prefix(content.active()))
        return scheduler

    # every 3 hours Kyiv time: 00:00, 03:00, ..., 21:00
    scheduler.add_job(
        hourly_bam,
        "cron",
        hour="*/3",
        minute=0,
        # nobody is awake to take the loot in quiet hours, the same ones as for the quiz
        kwargs={"bot": bot, "db": db, "chat_id": chat_id, "quiet_hours": quiet_hours},
    )
    if quiz_schedule_enabled:
        scheduler.add_job(
            scheduled_question,
            "interval",
            minutes=20,
            kwargs={"bot": bot, "db": db, "chat_id": chat_id, "quiet_hours": quiet_hours},
        )
    if quote_of_the_day_enabled:
        scheduler.add_job(
            quote_of_the_day, "cron", hour=19, minute=0, kwargs={"bot": bot, "db": db, "chat_id": chat_id}
        )
    if who_poll_enabled:
        scheduler.add_job(who_poll, "cron", hour=12, minute=0, kwargs={"bot": bot, "db": db, "chat_id": chat_id})
    if weekly_summary_enabled:
        scheduler.add_job(
            weekly_summary,
            "cron",
            day_of_week="sun",
            hour=20,
            minute=0,
            kwargs={"bot": bot, "db": db, "chat_id": chat_id},
        )
    if miss_you_enabled:
        scheduler.add_job(we_miss_you, "cron", hour=15, minute=0, kwargs={"bot": bot, "db": db, "chat_id": chat_id})
    return scheduler
