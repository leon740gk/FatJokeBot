from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, ReplyParameters

from telegram_bots.bots.fat_joke.db import quiz as quiz_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.scheduler import ask_question, build_keyboard
from telegram_bots.bots.fat_joke.services import iq, quiz
from telegram_bots.knowledge_base.fat_joke.reaction_data import commands_responses

router = Router(name="commands")


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(commands_responses["help"])


@router.message(Command("stream"))
async def stream_command(message: Message):
    await message.answer(commands_responses["stream"])


@router.message(Command("chat_id"))
async def chat_id_command(message: Message):
    # handy for FAT_JOKE_MAIN_CHAT_ID in .env
    await message.answer(f"ID этого чата: {message.chat.id}")


@router.message(Command("show_iq"))
async def show_iq_command(message: Message, db):
    await message.answer(iq.format_iq_table(users_db.get_all_iq(db)))


def discipline_from_args(command: CommandObject, db):
    """The discipline named after the command, or the current one; None if the name is unknown."""
    if not command.args:
        return quiz.current_discipline(db)
    return quiz.find_discipline(command.args)


UNKNOWN_TOPIC = "Не знаю такой темы 🤔\n\n"


@router.message(Command("show_leaders"))
async def show_leaders_command(message: Message, command: CommandObject, db):
    discipline = discipline_from_args(command, db)
    if not discipline:
        await message.answer(UNKNOWN_TOPIC + quiz.format_disciplines(quiz.current_discipline(db)))
        return
    season = quiz_db.current_season(db, discipline)
    await message.answer(quiz.format_leaders(quiz_db.get_leaders(db, discipline, season), discipline, season))


@router.message(Command("leaders"))
async def leaders_command(message: Message, db):
    rows = []
    for discipline in quiz.DISCIPLINES:
        season = quiz_db.current_season(db, discipline)
        rows.append((discipline, season, quiz_db.get_leaders(db, discipline, season)))
    await message.answer(quiz.format_all_leaders(rows))


@router.message(Command("already_answered_questions"))
async def already_answered_command(message: Message, command: CommandObject, db):
    discipline = discipline_from_args(command, db)
    if not discipline:
        await message.answer(UNKNOWN_TOPIC + quiz.format_disciplines(quiz.current_discipline(db)))
        return
    season = quiz_db.current_season(db, discipline)
    numbers = quiz_db.get_answered_numbers(db, message.from_user.id, discipline, season)
    await message.answer(quiz.format_answered(numbers))


OWN_QUESTION_FIRST = "Сначала ответь на свой вопрос 👆"


async def quiz_for(message: Message, db, discipline):
    """Asks the sender a question of their own, unless they still have one open."""
    own = quiz_db.get_open_question_of(db, message.chat.id, message.from_user.id)
    if own:
        await message.answer(
            OWN_QUESTION_FIRST, reply_parameters=ReplyParameters(message_id=own[0], allow_sending_without_reply=True)
        )
        return
    await ask_question(message.bot, db, message.chat.id, discipline, asked_by=message.from_user.id)


@router.message(Command("quiz"))
async def quiz_command(message: Message, command: CommandObject, db):
    discipline = quiz.find_discipline(command.args) if command.args else None
    if not discipline:
        # the topic buttons work only for whoever sent /quiz
        picker = quiz.render_topic_picker(message.from_user.id)
        prefix = UNKNOWN_TOPIC if command.args else ""
        await message.answer(prefix + picker.text, reply_markup=build_keyboard(picker))
        return
    await quiz_for(message, db, discipline)


async def is_chat_admin(message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return True
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR)


@router.message(Command("discipline"))
async def discipline_command(message: Message, command: CommandObject, db):
    if not command.args:
        await message.answer(quiz.format_disciplines(quiz.current_discipline(db)))
        return
    code = quiz.find_discipline(command.args)
    if not code:
        await message.answer(UNKNOWN_TOPIC + quiz.format_disciplines(quiz.current_discipline(db)))
        return
    if not await is_chat_admin(message):
        await message.answer("Менять дисциплину могут только админы чата 😈")
        return
    quiz.set_discipline(db, code)
    await message.answer(f"Теперь вопросы по расписанию на тему {quiz.title(code)}! Следующий вопрос: /quiz")
