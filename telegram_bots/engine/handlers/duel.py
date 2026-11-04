import random
import time

from aiogram import F, Router
from aiogram.enums import MessageEntityType
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from telegram_bots.engine.content import kb
from telegram_bots.engine.db import bets as bets_db
from telegram_bots.engine.db import duels as duels_db
from telegram_bots.engine.db import users as users_db
from telegram_bots.engine.scheduler import build_keyboard, duelist_names, finish_duel, settle_bets
from telegram_bots.engine.services import achievements, bets, duel, quiz
from telegram_bots.engine.services.people import display_name
from telegram_bots.engine.services.quiz import RenderedQuestion

router = Router(name="duel")


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
        await message.answer(kb.texts.duel_unknown_person if known else kb.texts.duel_how_to)
        return
    challenger = message.from_user
    if opponent[0] == challenger.id:
        await message.answer(kb.texts.duel_self)
        return
    discipline = quiz.find_discipline(" ".join(rest)) if rest else None
    if rest and not discipline:
        await message.answer(kb.texts.unknown_topic + quiz.format_disciplines(quiz.current_discipline(db)))
        return
    for user_id in (challenger.id, opponent[0]):
        if duels_db.open_for(db, message.chat.id, user_id):
            busy = kb.texts.duel_busy_you if user_id == challenger.id else kb.texts.duel_busy_opponent
            await message.answer(busy)
            return

    duel_id = duels_db.create(db, message.chat.id, challenger.id, opponent[0], discipline)
    text, keyboard = challenge_view(db, duel.from_row(duels_db.get(db, duel_id)))
    sent = await message.answer(text, reply_markup=keyboard)
    duels_db.set_message(db, duel_id, sent.message_id)


def first_names(db, current):
    names = {}
    for user_id in (current.challenger, current.opponent):
        profile = users_db.get_profile(db, user_id)
        names[user_id] = profile[1] if profile else str(user_id)
    return names


def challenge_view(db, current):
    """Text and buttons of a challenge still waiting: accept, decline and bet on either duelist."""
    names = duelist_names(db, current)
    short = first_names(db, current)
    text = duel.challenge_text(names[current.challenger], names[current.opponent], current.discipline)
    text += "\n\n" + bets.bank_line(bets_db.for_duel(db, current.id), short)
    stake = bets.BUTTON_STAKE
    rows = [
        [
            (kb.texts.duel_accept_button, duel.challenge_callback(current.id, duel.ACCEPT)),
            (kb.texts.duel_decline_button, duel.challenge_callback(current.id, duel.DECLINE)),
        ],
        [
            (kb.texts.bet_button.format(stake=stake, name=short[side]), bets.callback(current.id, side))
            for side in short
        ],
    ]
    return text, build_keyboard(RenderedQuestion(text, rows))


def place_bet(db, current, user_id, side, amount):
    """Error text, or None after the bet is made."""
    error = bets.check(db, current, user_id, side, amount, achievements.battle_points(db, user_id))
    if not error:
        bets_db.add(db, current.id, user_id, side, amount)
    return error


async def refresh_challenge(bot, db, current):
    text, keyboard = challenge_view(db, current)
    await bot.edit_message_text(text, chat_id=current.chat_id, message_id=current.message_id, reply_markup=keyboard)


@router.callback_query(F.data.startswith("bet "))
async def bet_callback(callback: CallbackQuery, db):
    parsed = bets.parse_callback(callback.data)
    current = duel.from_row(duels_db.get(db, parsed[0])) if parsed else None
    if not current:
        await callback.answer(kb.texts.duel_over)
        return
    error = place_bet(db, current, callback.from_user.id, parsed[1], bets.BUTTON_STAKE)
    if error:
        await callback.answer(error, show_alert=True)
        return
    total = bets_db.get(db, current.id, callback.from_user.id)[1]
    await callback.answer(kb.texts.bet_taken.format(total=total))
    await refresh_challenge(callback.bot, db, current)


@router.message(Command("bet"))
async def bet_command(message: Message, command: CommandObject, db):
    words = (command.args or "").split()
    amount = next((int(word) for word in words if word.isdigit()), None)
    side, _ = find_opponent(message, db, [word for word in words if not word.isdigit()])
    if amount is None or not side:
        await message.answer(kb.texts.bet_how_to.format(max=bets.MAX_BET))
        return
    duel_id = duels_db.open_for(db, message.chat.id, side[0])
    current = duel.from_row(duels_db.get(db, duel_id)) if duel_id else None
    if not current or current.status != "pending":
        await message.answer(kb.texts.bet_no_duel.format(name=side[1]))
        return
    error = place_bet(db, current, message.from_user.id, side[0], amount)
    if error:
        await message.answer(error)
        return
    await message.answer(kb.texts.bet_placed.format(who=display_name(message.from_user), amount=amount, name=side[1]))
    await refresh_challenge(message.bot, db, current)


@router.callback_query(F.data.startswith("duel "))
async def duel_callback(callback: CallbackQuery, db):
    parsed = duel.parse_callback(callback.data)
    current = duel.from_row(duels_db.get(db, parsed[1])) if parsed else None
    if not current or not isinstance(callback.message, Message):
        await callback.answer(kb.texts.duel_over)
        return
    action, _, option = parsed
    if action == "a":
        await answer(callback, db, current, option)
    else:
        await respond(callback, db, current, action)


async def respond(callback: CallbackQuery, db, current, action):
    user_id = callback.from_user.id
    if current.status != "pending":
        await callback.answer(kb.texts.duel_stale)
        return
    names = duelist_names(db, current)
    if action == duel.DECLINE and user_id in (current.challenger, current.opponent):
        if duels_db.set_status(db, current.id, "pending", "declined"):
            await callback.answer()
            template = kb.texts.duel_cancelled if user_id == current.challenger else kb.texts.duel_declined
            refunded = kb.texts.bets_refunded if settle_bets(db, current, None) else ""
            await callback.message.edit_text(template.format(name=names[user_id]) + refunded)
        return
    if user_id != current.opponent:
        await callback.answer(kb.texts.duel_not_you, show_alert=True)
        return
    question = duel.pick_question(current.discipline)
    if not duels_db.start(db, current.id, question.number, question.discipline, time.time()):
        await callback.answer(kb.texts.duel_stale)
        return
    await callback.answer(kb.texts.duel_go)
    rendered = duel.render(question, current.id, names[current.challenger], names[current.opponent], random)
    await callback.message.edit_text(rendered.text, reply_markup=build_keyboard(rendered))


async def answer(callback: CallbackQuery, db, current, option):
    side = current.side_of(callback.from_user.id)
    if current.status != "active":
        await callback.answer(kb.texts.duel_over)
        return
    if not side:
        await callback.answer(kb.texts.duel_watch_only, show_alert=True)
        return
    if not duels_db.save_answer(db, current.id, side, option, time.time() - current.started_at):
        await callback.answer(kb.texts.duel_already_answered)
        return
    current = duel.from_row(duels_db.get(db, current.id))
    if current.both_answered():
        await callback.answer()
        await finish_duel(callback.bot, db, current)
    else:
        await callback.answer(kb.texts.duel_answer_taken)
