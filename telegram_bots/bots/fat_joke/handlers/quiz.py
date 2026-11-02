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
    parsed = quiz.parse_topic_callback(callback.data)
    if not isinstance(message, Message) or not parsed:
        await callback.answer("Эта кнопка уже не работает, напишите /quiz")
        return
    discipline, owner = parsed
    user_id = callback.from_user.id
    if owner and owner != user_id:
        await callback.answer("Это не твой /quiz 😉 Вызови свой: /quiz", show_alert=True)
        return
    if quiz_db.is_quiz_message(db, message.chat.id, message.message_id):
        # the topic on this message was picked a moment earlier
        await callback.answer("Тему уже выбрали")
        return
    if quiz.limit_reached(db, user_id):
        # the picker was sent before the limit ran out
        await callback.answer(quiz.limit_text(), show_alert=True)
        return
    if quiz_db.get_open_question_of(db, message.chat.id, user_id):
        await callback.answer("Сначала ответь на свой вопрос, он выше 👆", show_alert=True)
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
        await callback.answer("Этот вопрос уже закрыт")
        return

    result = quiz.process_answer(db, callback.from_user.id, message.chat.id, message.message_id, callback.data)
    logger.info("answer from %s: %s -> %s", callback.from_user.id, callback.data, result.outcome.value)
    if result.outcome is Outcome.CLOSED:
        await callback.answer("Этот вопрос уже закрыт")
        return
    if result.outcome is Outcome.NOT_YOURS:
        await callback.answer(f"Ворюга! 😈 Это вопрос для {result.text}. Вызови свой: /quiz", show_alert=True)
        return

    await callback.answer()
    kind, file_id = OUTCOME_MEDIA[result.outcome]
    if kind == "animation":
        await message.answer_animation(file_id)
    await message.edit_text(result.text)
    if kind == "sticker":
        await message.answer_sticker(file_id)
