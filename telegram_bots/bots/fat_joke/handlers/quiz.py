import logging

from aiogram import Router
from aiogram.types import CallbackQuery, Message

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


@router.callback_query()
async def answer_callback(callback: CallbackQuery, db):
    message = callback.message
    if not isinstance(message, Message):
        # too old for the bot to edit
        await callback.answer("Це питання вже закрите")
        return

    result = quiz.process_answer(db, callback.from_user.id, message.chat.id, message.message_id, callback.data)
    logger.info("answer from %s: %s -> %s", callback.from_user.id, callback.data, result.outcome.value)
    if result.outcome is Outcome.CLOSED:
        await callback.answer("Це питання вже закрите")
        return

    await callback.answer()
    kind, file_id = OUTCOME_MEDIA[result.outcome]
    if kind == "animation":
        await message.answer_animation(file_id)
    await message.edit_text(result.text)
    if kind == "sticker":
        await message.answer_sticker(file_id)
