import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from telegram_bots.bots.fat_joke.db import quiz as quiz_db
from telegram_bots.bots.fat_joke.scheduler import ask_question
from telegram_bots.bots.fat_joke.services import quiz
from telegram_bots.bots.fat_joke.services.quiz import Outcome
from telegram_bots.knowledge_base.fat_joke.reaction_data import genuis_sticker, red_blink, smart_nigga

logger = logging.getLogger(__name__)
router = Router(name="quiz")

OUTCOME_MEDIA = {
    Outcome.CORRECT: ("sticker", smart_nigga),
    Outcome.WRONG: ("sticker", genuis_sticker),
    Outcome.CHEATER: ("animation", red_blink),
}


@router.callback_query(F.data.startswith("t "))
async def topic_callback(callback: CallbackQuery, db):
    message = callback.message
    discipline = quiz.parse_topic_callback(callback.data)
    if not isinstance(message, Message) or not discipline:
        await callback.answer("Эта кнопка уже не работает, напишите /quiz")
        return
    if quiz_db.is_quiz_message(db, message.chat.id, message.message_id):
        # someone else picked a topic on this message a moment earlier
        await callback.answer("Тему уже выбрали")
        return
    if quiz_db.get_open_question(db, message.chat.id, discipline):
        await callback.answer(
            f"Сначала ответьте на предыдущий вопрос по теме {quiz.title(discipline)}!", show_alert=True
        )
        return
    await callback.answer()
    await ask_question(callback.bot, db, message.chat.id, discipline, into_message_id=message.message_id)


@router.callback_query()
async def answer_callback(callback: CallbackQuery, db):
    message = callback.message
    if not isinstance(message, Message):
        # too old for the bot to edit
        await callback.answer("Этот вопрос уже закрыт")
        return

    result = quiz.process_answer(db, callback.from_user.id, message.chat.id, message.message_id, callback.data)
    logger.info("answer from %s: %s -> %s", callback.from_user.id, callback.data, result.outcome.value)
    if result.outcome is Outcome.CLOSED:
        await callback.answer("Этот вопрос уже закрыт")
        return

    await callback.answer()
    kind, file_id = OUTCOME_MEDIA[result.outcome]
    if kind == "animation":
        await message.answer_animation(file_id)
    await message.edit_text(result.text)
    if kind == "sticker":
        await message.answer_sticker(file_id)
