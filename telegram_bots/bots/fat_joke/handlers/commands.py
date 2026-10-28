from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bots.bots.fat_joke.db import quiz as quiz_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.services import iq, quiz
from telegram_bots.knowledge_base.fat_joke.reaction_data import commands_responses

router = Router(name="commands")


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(commands_responses["help"])


@router.message(Command("stream"))
async def stream_command(message: Message):
    await message.answer(commands_responses["stream"])


@router.message(Command("show_iq"))
async def show_iq_command(message: Message, db):
    await message.answer(iq.format_iq_table(users_db.get_all_iq(db)))


@router.message(Command("show_leaders"))
async def show_leaders_command(message: Message, db):
    await message.answer(quiz.format_leaders(quiz_db.get_leaders(db, quiz.CURRENT_DISCIPLINE)))


@router.message(Command("already_answered_questions"))
async def already_answered_command(message: Message, db):
    numbers = quiz_db.get_answered_numbers(db, message.from_user.id, quiz.CURRENT_DISCIPLINE)
    await message.answer(quiz.format_answered(numbers))
