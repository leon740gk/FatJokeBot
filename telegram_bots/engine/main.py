"""Runs one bot: python -m telegram_bots.bots.<bot>.main calls run("<bot>")."""

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand

from telegram_bots.config import Settings, load_settings, require_token
from telegram_bots.engine import content
from telegram_bots.engine.content import kb
from telegram_bots.engine.db.backup import backup_if_stale
from telegram_bots.engine.db.connection import Database
from telegram_bots.engine.db.schema import init_schema
from telegram_bots.engine.handlers import (
    birthdays,
    commands,
    duel,
    fat_day,
    loot,
    members,
    party,
    profile,
    quiz,
    quotes,
    reactions,
    who,
)
from telegram_bots.engine.middlewares import UserActivityMiddleware
from telegram_bots.engine.scheduler import check_chat, create_scheduler
from telegram_bots.engine.services.quiet_hours import parse_quiet_hours


async def set_commands(bot):
    """Sends the "/" command menu to Telegram, so it always matches the code."""
    try:
        commands = kb.reaction_data.bot_commands
        await bot.set_my_commands([BotCommand(command=name, description=text) for name, text in commands.items()])
    except TelegramAPIError as error:
        logging.getLogger(__name__).warning("can't set the command menu: %s", error.message)


# commands go first, so "/help" never reaches the keyword reactions;
# party, loot and duel buttons go before quiz, which takes every other button press
ROUTERS = (
    commands.router,
    members.router,
    birthdays.router,
    quotes.router,
    fat_day.router,
    profile.router,
    who.router,
    party.router,
    loot.router,
    duel.router,
    quiz.router,
    reactions.router,
)


def build_dispatcher(db, settings=None):
    """settings reach the handlers as the `settings` argument, like db."""
    dispatcher = Dispatcher(db=db, settings=settings or Settings(bot=content.active()))
    dispatcher.message.outer_middleware(UserActivityMiddleware())
    dispatcher.callback_query.outer_middleware(UserActivityMiddleware())
    dispatcher.include_routers(*ROUTERS)
    return dispatcher


async def main(settings):
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if settings.log_level != "DEBUG":
        # APScheduler logs two lines for every run of the every-minute job; errors still show up
        logging.getLogger("apscheduler").setLevel(logging.WARNING)
    if Path(settings.db_path).exists():
        backup_if_stale(settings.db_path, settings.backup_dir)
    db = Database(settings.db_path)
    init_schema(db)

    bot = Bot(require_token(settings))
    dispatcher = build_dispatcher(db, settings)

    scheduler = create_scheduler(
        bot,
        db,
        settings.main_chat_id,
        settings.miss_you_enabled,
        db_path=settings.db_path,
        backup_dir=settings.backup_dir,
        answer_minutes=settings.quiz_answer_minutes,
        quiz_schedule_enabled=settings.quiz_schedule_enabled,
        quiet_hours=parse_quiet_hours(settings.quiz_quiet_hours),
        quote_of_the_day_enabled=settings.quote_of_the_day_enabled,
        weekly_summary_enabled=settings.weekly_summary_enabled,
        who_poll_enabled=settings.who_poll_enabled,
        birthdays_enabled=settings.birthdays_enabled,
    )
    scheduler.start()
    try:
        # same as skip_pending in the old bot: ignore messages sent while it was offline
        await bot.delete_webhook(drop_pending_updates=True)
        await set_commands(bot)
        if settings.main_chat_id:
            await check_chat(bot, settings.main_chat_id)
        # chat_member updates (joins and leaves) only come when asked for explicitly
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        db.close()


def run(bot):
    """bot is the folder in telegram_bots/knowledge_base with its texts; its settings are <BOT>_... in .env."""
    content.activate(bot)
    asyncio.run(main(load_settings(bot)))
