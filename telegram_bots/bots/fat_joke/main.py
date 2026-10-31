import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand

from telegram_bots.bots.fat_joke.db.backup import backup_if_stale
from telegram_bots.bots.fat_joke.db.connection import Database
from telegram_bots.bots.fat_joke.db.schema import init_schema
from telegram_bots.bots.fat_joke.handlers import commands, fat_day, members, party, quiz, quotes, reactions
from telegram_bots.bots.fat_joke.middlewares import UserActivityMiddleware
from telegram_bots.bots.fat_joke.scheduler import check_chat, create_scheduler
from telegram_bots.bots.fat_joke.services.quiet_hours import parse_quiet_hours
from telegram_bots.config import (
    BACKUP_DIR,
    DB_PATH,
    LOG_LEVEL,
    MAIN_CHAT_ID,
    MISS_YOU_ENABLED,
    QUIZ_ANSWER_MINUTES,
    QUIZ_QUIET_HOURS,
    QUIZ_SCHEDULE_ENABLED,
    QUOTE_OF_THE_DAY_ENABLED,
    get_bot_token,
)
from telegram_bots.knowledge_base.fat_joke.reaction_data import bot_commands


async def set_commands(bot):
    """Sends the "/" command menu to Telegram, so it always matches the code."""
    try:
        await bot.set_my_commands([BotCommand(command=name, description=text) for name, text in bot_commands.items()])
    except TelegramAPIError as error:
        logging.getLogger(__name__).warning("can't set the command menu: %s", error.message)


# commands go first, so "/help" never reaches the keyword reactions;
# party buttons go before quiz, which takes every other button press
ROUTERS = (commands.router, members.router, quotes.router, fat_day.router, party.router, quiz.router, reactions.router)


def build_dispatcher(db):
    dispatcher = Dispatcher(db=db)
    dispatcher.message.outer_middleware(UserActivityMiddleware())
    dispatcher.callback_query.outer_middleware(UserActivityMiddleware())
    dispatcher.include_routers(*ROUTERS)
    return dispatcher


async def main():
    logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if LOG_LEVEL != "DEBUG":
        # APScheduler logs two lines for every run of the every-minute job; errors still show up
        logging.getLogger("apscheduler").setLevel(logging.WARNING)
    if Path(DB_PATH).exists():
        backup_if_stale(DB_PATH, BACKUP_DIR)
    db = Database(DB_PATH)
    init_schema(db)

    bot = Bot(get_bot_token())
    dispatcher = build_dispatcher(db)

    scheduler = create_scheduler(
        bot,
        db,
        MAIN_CHAT_ID,
        MISS_YOU_ENABLED,
        QUOTE_OF_THE_DAY_ENABLED,
        db_path=DB_PATH,
        backup_dir=BACKUP_DIR,
        answer_minutes=QUIZ_ANSWER_MINUTES,
        quiz_schedule_enabled=QUIZ_SCHEDULE_ENABLED,
        quiet_hours=parse_quiet_hours(QUIZ_QUIET_HOURS),
        quote_of_the_day_enabled=QUOTE_OF_THE_DAY_ENABLED,
    )
    scheduler.start()
    try:
        # same as skip_pending in the old bot: ignore messages sent while it was offline
        await bot.delete_webhook(drop_pending_updates=True)
        await set_commands(bot)
        if MAIN_CHAT_ID:
            await check_chat(bot, MAIN_CHAT_ID)
        # chat_member updates (joins and leaves) only come when asked for explicitly
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
