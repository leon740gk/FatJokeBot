import random
import time

from aiogram import F, Router
from aiogram.enums import MessageEntityType
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from telegram_bots.bots.fat_joke.db import duels as duels_db
from telegram_bots.bots.fat_joke.db import users as users_db
from telegram_bots.bots.fat_joke.scheduler import build_keyboard, duelist_names, finish_duel
from telegram_bots.bots.fat_joke.services import duel, quiz
from telegram_bots.bots.fat_joke.services.people import display_name, mention
from telegram_bots.bots.fat_joke.services.quiz import RenderedQuestion

router = Router(name="duel")
HOW_TO = "Кого вызываешь? Ответь /duel на сообщение соперника или напиши /duel @ник (можно с темой: /duel @ник мобла)"


def find_opponent(message: Message, db, words):
    """(telegram_id, name, username) of the one challenged and the words left for the topic."""
    replied = message.reply_to_message
    if replied and replied.from_user and not replied.from_user.is_bot:
        user = replied.from_user
        users_db.register(db, user)
        return (user.id, display_name(user), user.username), words
    for entity in message.entities or []:
        if entity.type == MessageEntityType.TEXT_MENTION and entity.user and not entity.user.is_bot:
            users_db.register(db, entity.user)
            name = entity.extract_from(message.text)
            rest = [word for word in words if word not in name.split()]
            return (entity.user.id, display_name(entity.user), entity.user.username), rest
    for word in words:
        if word.startswith("@"):
            profile = users_db.find_by_username(db, word[1:])
            return profile, [other for other in words if other != word]
    return None, words


@router.message(Command("duel"))
async def duel_command(message: Message, command: CommandObject, db):
    words = (command.args or "").split()
    opponent, rest = find_opponent(message, db, words)
    if not opponent:
        known = any(word.startswith("@") for word in words)
        await message.answer("Не знаю такого человека в чате 🤔" if known else HOW_TO)
        return
    challenger = message.from_user
    if opponent[0] == challenger.id:
        await message.answer("Дуэль с самим собой? Это называется шизофрения 🙃")
        return
    discipline = quiz.find_discipline(" ".join(rest)) if rest else None
    if rest and not discipline:
        await message.answer("Не знаю такой темы 🤔\n\n" + quiz.format_disciplines(quiz.current_discipline(db)))
        return
    for user_id in (challenger.id, opponent[0]):
        if duels_db.open_for(db, message.chat.id, user_id):
            busy = "У тебя" if user_id == challenger.id else "У соперника"
            await message.answer(f"{busy} уже есть незаконченная дуэль ⚔️")
            return

    duel_id = duels_db.create(db, message.chat.id, challenger.id, opponent[0], discipline)
    buttons = RenderedQuestion(
        "",
        [
            [
                ("⚔️ Принять", duel.challenge_callback(duel_id, duel.ACCEPT)),
                ("🏳️ Отказаться", duel.challenge_callback(duel_id, duel.DECLINE)),
            ]
        ],
    )
    text = duel.challenge_text(
        mention(display_name(challenger), challenger.username), mention(*opponent[1:]), discipline
    )
    sent = await message.answer(text, reply_markup=build_keyboard(buttons))
    duels_db.set_message(db, duel_id, sent.message_id)


@router.callback_query(F.data.startswith("duel "))
async def duel_callback(callback: CallbackQuery, db):
    parsed = duel.parse_callback(callback.data)
    current = duel.from_row(duels_db.get(db, parsed[1])) if parsed else None
    if not current or not isinstance(callback.message, Message):
        await callback.answer("Эта дуэль уже закончилась")
        return
    action, _, option = parsed
    if action == "a":
        await answer(callback, db, current, option)
    else:
        await respond(callback, db, current, action)


async def respond(callback: CallbackQuery, db, current, action):
    user_id = callback.from_user.id
    if current.status != "pending":
        await callback.answer("Вызов уже не актуален")
        return
    names = duelist_names(db, current)
    if action == duel.DECLINE and user_id in (current.challenger, current.opponent):
        if duels_db.set_status(db, current.id, "pending", "declined"):
            await callback.answer()
            who = "отменил(а) вызов" if user_id == current.challenger else "отказался(ась) от дуэли"
            await callback.message.edit_text(f"🏳️ {names[user_id]} {who}.")
        return
    if user_id != current.opponent:
        await callback.answer("Это не тебя вызвали 🍿", show_alert=True)
        return
    question = duel.pick_question(current.discipline)
    if not duels_db.start(db, current.id, question.number, question.discipline, time.time()):
        await callback.answer("Вызов уже не актуален")
        return
    await callback.answer("Поехали! ⚔️")
    rendered = duel.render(question, current.id, names[current.challenger], names[current.opponent], random)
    await callback.message.edit_text(rendered.text, reply_markup=build_keyboard(rendered))


async def answer(callback: CallbackQuery, db, current, option):
    side = current.side_of(callback.from_user.id)
    if current.status != "active":
        await callback.answer("Эта дуэль уже закончилась")
        return
    if not side:
        await callback.answer("Ты не участвуешь в этой дуэли, просто смотри 🍿", show_alert=True)
        return
    if not duels_db.save_answer(db, current.id, side, option, time.time() - current.started_at):
        await callback.answer("Ты уже ответил(а), ждём соперника ⏳")
        return
    current = duel.from_row(duels_db.get(db, current.id))
    if current.both_answered():
        await callback.answer()
        await finish_duel(callback.bot, db, current)
    else:
        await callback.answer("Ответ принят, ждём соперника ⏳")
