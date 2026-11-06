from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, ReplyParameters

from telegram_bots.engine.content import kb
from telegram_bots.engine.db import quiz as quiz_db
from telegram_bots.engine.db import users as users_db
from telegram_bots.engine.scheduler import ask_question, build_keyboard
from telegram_bots.engine.services import iq, quiz

router = Router(name="commands")


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(kb.reaction_data.commands_responses["help"])


@router.message(Command("stream"))
async def stream_command(message: Message):
    await message.answer(kb.reaction_data.commands_responses["stream"])


@router.message(Command("chat_id"))
async def chat_id_command(message: Message):
    # handy for <BOT>_MAIN_CHAT_ID in .env
    await message.answer(kb.texts.chat_id.format(id=message.chat.id))


@router.message(Command("show_iq"))
async def show_iq_command(message: Message, db):
    await message.answer(iq.format_iq_table(users_db.get_all_iq(db)))


def discipline_from_args(command: CommandObject, db):
    """The discipline named after the command, or the current one; None if the name is unknown."""
    if not command.args:
        return quiz.current_discipline(db)
    return quiz.find_discipline(command.args)


@router.message(Command("show_leaders"))
async def show_leaders_command(message: Message, command: CommandObject, db):
    discipline = discipline_from_args(command, db)
    if not discipline:
        await message.answer(kb.texts.unknown_topic + quiz.format_disciplines(quiz.current_discipline(db)))
        return
    season = quiz_db.current_season(db, discipline)
    await message.answer(quiz.format_leaders(quiz_db.get_leaders(db, discipline, season), discipline, season))


@router.message(Command("leaders"))
async def leaders_command(message: Message, db):
    rows = []
    for discipline in quiz.disciplines():
        season = quiz_db.current_season(db, discipline)
        rows.append((discipline, season, quiz_db.get_leaders(db, discipline, season)))
    await message.answer(quiz.format_all_leaders(rows))


@router.message(Command("already_answered_questions"))
async def already_answered_command(message: Message, command: CommandObject, db):
    discipline = discipline_from_args(command, db)
    if not discipline:
        await message.answer(kb.texts.unknown_topic + quiz.format_disciplines(quiz.current_discipline(db)))
        return
    if message.sender_chat:
        # sent on behalf of the chat: no way to know whose answers to show
        await message.answer(kb.texts.answered_anonymous)
        return
    season = quiz_db.current_season(db, discipline)
    numbers = quiz_db.get_answered_numbers(db, message.from_user.id, discipline, season)
    await message.answer(quiz.format_answered(numbers))


def quiz_caller(message: Message):
    """Who called /quiz, or None when it was sent on behalf of a chat.

    An anonymous admin or a channel shows up as GroupAnonymousBot or Channel_Bot, and the real person
    presses the buttons under their own id, so such a /quiz belongs to nobody: anyone may take it.
    """
    return None if message.sender_chat else message.from_user.id


async def quiz_for(message: Message, db, discipline):
    """Asks the sender a question of their own, unless they still have one open."""
    caller = quiz_caller(message)
    own = caller and quiz_db.get_open_question_of(db, message.chat.id, caller)
    if own:
        await message.answer(
            kb.texts.own_question_first,
            reply_parameters=ReplyParameters(message_id=own[0], allow_sending_without_reply=True),
        )
        return
    await ask_question(message.bot, db, message.chat.id, discipline, asked_by=caller)


@router.message(Command("quiz"))
async def quiz_command(message: Message, command: CommandObject, db, settings):
    caller = quiz_caller(message)
    if caller and quiz.limit_reached(db, caller, settings.quiz_daily_limit):
        await message.answer(quiz.limit_text(settings.quiz_daily_limit))
        return
    discipline = quiz.find_discipline(command.args) if command.args else None
    if not discipline:
        # the topic buttons work only for whoever sent /quiz; whoever picks the topic gets the question
        picker = quiz.render_topic_picker(caller)
        prefix = kb.texts.unknown_topic if command.args else ""
        await message.answer(prefix + picker.text, reply_markup=build_keyboard(picker))
        return
    await quiz_for(message, db, discipline)


async def is_chat_admin(message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return True
    if message.sender_chat:
        # only admins can write as the group itself; a linked channel is not an admin
        return message.sender_chat.id == message.chat.id
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR)


@router.message(Command("discipline"))
async def discipline_command(message: Message, command: CommandObject, db):
    if not command.args:
        await message.answer(quiz.format_disciplines(quiz.current_discipline(db)))
        return
    code = quiz.find_discipline(command.args)
    if not code:
        await message.answer(kb.texts.unknown_topic + quiz.format_disciplines(quiz.current_discipline(db)))
        return
    if not await is_chat_admin(message):
        await message.answer(kb.texts.discipline_admins_only)
        return
    quiz.set_discipline(db, code)
    await message.answer(kb.texts.discipline_set.format(topic=quiz.title(code)))
