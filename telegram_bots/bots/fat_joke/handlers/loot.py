import random

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from telegram_bots.bots.fat_joke.db import loot as loot_db
from telegram_bots.bots.fat_joke.services import achievements, loot
from telegram_bots.bots.fat_joke.services.people import display_name, mention
from telegram_bots.knowledge_base.fat_joke.mlbb_data import gone_line, gone_phrase, late_phrases

router = Router(name="loot")


@router.callback_query(F.data == loot.CALLBACK)
async def loot_callback(callback: CallbackQuery, db):
    message = callback.message
    found = isinstance(message, Message) and loot_db.find(db, message.chat.id, message.message_id)
    if not found:
        await callback.answer(gone_phrase)
        return
    kind_code, _, taken_by = found
    if taken_by:
        await callback.answer(random.choice(late_phrases))
        return

    user = callback.from_user
    old_points = achievements.battle_points(db, user.id)
    bam_text = loot.bam_part(message.text)
    if not loot_db.claim(db, message.chat.id, message.message_id, user.id, loot.LOOT_MINUTES):
        await callback.answer(gone_phrase)
        await message.edit_text(f"{bam_text}\n\n{gone_line}")
        return

    kind = loot.KINDS[kind_code]
    await callback.answer(f"+{kind.points} BP! 💰")
    who = mention(display_name(user), user.username)
    rank_up = achievements.rank_up_line(who, old_points, achievements.battle_points(db, user.id))
    await message.edit_text(loot.taken_text(bam_text, kind, who, [rank_up] if rank_up else []))
