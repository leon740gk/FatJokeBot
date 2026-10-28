import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher

from telegram_bots.bots.fat_joke.db.backup import backup_if_stale
from telegram_bots.bots.fat_joke.db.connection import Database
from telegram_bots.bots.fat_joke.db.schema import init_schema
from telegram_bots.bots.fat_joke.handlers import commands, quiz, reactions
from telegram_bots.bots.fat_joke.middlewares import UserActivityMiddleware
from telegram_bots.bots.fat_joke.scheduler import create_scheduler
from telegram_bots.config import BACKUP_DIR, DB_PATH, LOG_LEVEL, MAIN_CHAT_ID, MISS_YOU_ENABLED, get_bot_token


def build_dispatcher(db):
    dispatcher = Dispatcher(db=db)
    dispatcher.message.outer_middleware(UserActivityMiddleware())
    dispatcher.callback_query.outer_middleware(UserActivityMiddleware())
    # commands go first, so "/help" never reaches the keyword reactions
    dispatcher.include_routers(commands.router, quiz.router, reactions.router)
    return dispatcher


async def main():
    logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if Path(DB_PATH).exists():
        backup_if_stale(DB_PATH, BACKUP_DIR)
    db = Database(DB_PATH)
    init_schema(db)

    bot = Bot(get_bot_token())
    dispatcher = build_dispatcher(db)

    scheduler = create_scheduler(bot, db, MAIN_CHAT_ID, MISS_YOU_ENABLED, db_path=DB_PATH, backup_dir=BACKUP_DIR)
    scheduler.start()
    try:
        # same as skip_pending in the old bot: ignore messages sent while it was offline
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
