from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

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
    await message.answer(f"ID цього чату: {message.chat.id}")


@router.message(Command("show_iq"))
async def show_iq_command(message: Message, db):
    await message.answer(iq.format_iq_table(users_db.get_all_iq(db)))


def discipline_from_args(command: CommandObject, db):
    """The discipline named after the command, or the current one; None if the name is unknown."""
    if not command.args:
        return quiz.current_discipline(db)
    return quiz.find_discipline(command.args)


UNKNOWN_TOPIC = "Не знаю такої теми 🤔\n\n"


@router.message(Command("show_leaders"))
async def show_leaders_command(message: Message, command: CommandObject, db):
    discipline = discipline_from_args(command, db)
    if not discipline:
        await message.answer(UNKNOWN_TOPIC + quiz.format_disciplines(quiz.current_discipline(db)))
        return
    season = quiz_db.current_season(db, discipline)
    await message.answer(quiz.format_leaders(quiz_db.get_leaders(db, discipline, season), discipline, season))


@router.message(Command("already_answered_questions"))
async def already_answered_command(message: Message, command: CommandObject, db):
    discipline = discipline_from_args(command, db)
    if not discipline:
        await message.answer(UNKNOWN_TOPIC + quiz.format_disciplines(quiz.current_discipline(db)))
        return
    season = quiz_db.current_season(db, discipline)
    numbers = quiz_db.get_answered_numbers(db, message.from_user.id, discipline, season)
    await message.answer(quiz.format_answered(numbers))


async def ask_if_free(message: Message, db, discipline, into_message_id=None):
    """Asks a question of the discipline unless one of it is already open in this chat."""
    if quiz_db.get_open_question(db, message.chat.id, discipline):
        return False
    await ask_question(message.bot, db, message.chat.id, discipline, into_message_id=into_message_id)
    return True


@router.message(Command("quiz"))
async def quiz_command(message: Message, command: CommandObject, db):
    if not command.args:
        picker = quiz.render_topic_picker()
        await message.answer(picker.text, reply_markup=build_keyboard(picker))
        return
    discipline = quiz.find_discipline(command.args)
    if not discipline:
        picker = quiz.render_topic_picker()
        await message.answer(UNKNOWN_TOPIC + picker.text, reply_markup=build_keyboard(picker))
        return
    if not await ask_if_free(message, db, discipline):
        await message.answer(f"Спочатку відповідайте на попереднє питання з теми {quiz.title(discipline)}! ☝️")


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
        await message.answer("Змінювати дисципліну можуть тільки адміни чату 😈")
        return
    quiz.set_discipline(db, code)
    await message.answer(f"Тепер питання за розкладом з теми {quiz.title(code)}! Наступне питання: /quiz")
