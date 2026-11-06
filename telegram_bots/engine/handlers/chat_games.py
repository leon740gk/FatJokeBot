import logging

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message, ReactionTypeEmoji, ReplyParameters

from telegram_bots.engine.content import kb
from telegram_bots.engine.db import chat_games as games_db
from telegram_bots.engine.scheduler import start_riddle, start_this_or_that, start_tonight_poll
from telegram_bots.engine.services import achievements, chat_games
from telegram_bots.engine.services.people import display_name, mention

logger = logging.getLogger(__name__)
router = Router(name="chat_games")
in_group = F.chat.type != ChatType.PRIVATE
# the bot's mark on an answer to the question of the day, so the person sees it counted
ANSWER_SEEN = "✍"


@router.message(Command("vs"))
async def this_or_that_command(message: Message, db):
    if message.chat.type == ChatType.PRIVATE:
        await message.answer(kb.texts.group_only)
    elif not await start_this_or_that(message.bot, db, message.chat.id):
        await message.answer(kb.texts.chat_games_off)


@router.message(Command("tonight"))
async def tonight_command(message: Message, db):
    if message.chat.type == ChatType.PRIVATE:
        await message.answer(kb.texts.group_only)
    elif not await start_tonight_poll(message.bot, db, message.chat.id):
        await message.answer(kb.texts.chat_games_off)


@router.message(Command("guess"))
async def guess_command(message: Message, db):
    if message.chat.type == ChatType.PRIVATE:
        await message.answer(kb.texts.group_only)
        return
    current = games_db.open_riddle(db, message.chat.id)
    if current:
        await message.answer(
            kb.texts.riddle_already_open,
            reply_parameters=ReplyParameters(message_id=current[1], allow_sending_without_reply=True),
        )
    elif not await start_riddle(message.bot, db, message.chat.id):
        await message.answer(kb.texts.chat_games_off)


async def solve_riddle(message: Message, db):
    """True if the message solved the open riddle of the chat."""
    current = games_db.open_riddle(db, message.chat.id)
    riddle = current and chat_games.get_riddle(current[2])
    if not riddle or not chat_games.is_answer(message.text, riddle):
        return False
    user = message.from_user
    points = chat_games.riddle_points(current[3])
    old_points = achievements.battle_points(db, user.id)
    if not games_db.solve_riddle(db, current[0], user.id, points):
        return False
    who = mention(display_name(user), user.username)
    lines = [kb.texts.riddle_solved.format(who=who, answer=riddle.answers[0], points=points, xp=kb.theme_data.points)]
    rank_up = achievements.rank_up_line(who, old_points, achievements.battle_points(db, user.id))
    if rank_up:
        lines.append(rank_up)
    await message.reply("\n".join(lines))
    return True


async def answer_daily_question(message: Message, db):
    replied = message.reply_to_message
    if not replied or not replied.from_user or replied.from_user.id != message.bot.id:
        return
    question_id = games_db.daily_question_id(db, message.chat.id, replied.message_id)
    if not question_id:
        return
    if games_db.answer_daily_question(db, question_id, message.from_user.id, chat_games.DAILY_ANSWER_POINTS):
        try:
            await message.react([ReactionTypeEmoji(emoji=ANSWER_SEEN)])
        except TelegramAPIError as error:
            logger.debug("can't react to the answer %s: %s", message.message_id, error.message)


@router.message(F.text, in_group)
async def chat_games_text(message: Message, db):
    if await solve_riddle(message, db):
        return
    await answer_daily_question(message, db)
    # the keyword reactions still get the message
    raise SkipHandler
