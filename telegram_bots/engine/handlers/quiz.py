import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from telegram_bots.engine.content import kb
from telegram_bots.engine.db import quiz as quiz_db
from telegram_bots.engine.scheduler import ask_question
from telegram_bots.engine.services import quiz
from telegram_bots.engine.services.quiz import Outcome

logger = logging.getLogger(__name__)
router = Router(name="quiz")


def outcome_media(outcome):
    """(kind, file id) the bot sends after the answer, from reaction_data of the bot."""
    data = kb.reaction_data
    return {
        Outcome.CORRECT: ("sticker", data.quiz_correct_sticker),
        Outcome.WRONG: ("sticker", data.quiz_wrong_sticker),
        Outcome.CHEATER: ("animation", data.quiz_cheater_animation),
    }[outcome]


@router.callback_query(F.data.startswith("t "))
async def topic_callback(callback: CallbackQuery, db, settings):
    message = callback.message
    parsed = quiz.parse_topic_callback(callback.data)
    if not isinstance(message, Message) or not parsed:
        await callback.answer(kb.texts.topic_button_dead)
        return
    discipline, owner = parsed
    user_id = callback.from_user.id
    if owner and owner != user_id:
        await callback.answer(kb.texts.topic_not_yours, show_alert=True)
        return
    if quiz_db.is_quiz_message(db, message.chat.id, message.message_id):
        # the topic on this message was picked a moment earlier
        await callback.answer(kb.texts.topic_taken)
        return
    if quiz.limit_reached(db, user_id, settings.quiz_daily_limit):
        # the picker was sent before the limit ran out
        await callback.answer(quiz.limit_text(settings.quiz_daily_limit), show_alert=True)
        return
    if quiz_db.get_open_question_of(db, message.chat.id, user_id):
        await callback.answer(kb.texts.own_question_above, show_alert=True)
        return
    await callback.answer()
    await ask_question(
        callback.bot, db, message.chat.id, discipline, into_message_id=message.message_id, asked_by=user_id
    )


@router.callback_query()
async def answer_callback(callback: CallbackQuery, db):
    message = callback.message
    if not isinstance(message, Message):
        # too old for the bot to edit
        await callback.answer(kb.texts.question_closed)
        return

    result = quiz.process_answer(db, callback.from_user.id, message.chat.id, message.message_id, callback.data)
    logger.info("answer from %s: %s -> %s", callback.from_user.id, callback.data, result.outcome.value)
    if result.outcome is Outcome.CLOSED:
        await callback.answer(kb.texts.question_closed)
        return
    if result.outcome is Outcome.NOT_YOURS:
        await callback.answer(kb.texts.question_not_yours.format(name=result.text), show_alert=True)
        return

    await callback.answer()
    kind, file_id = outcome_media(result.outcome)
    if kind == "animation":
        await message.answer_animation(file_id)
    await message.edit_text(result.text)
    if kind == "sticker":
        await message.answer_sticker(file_id)
