import logging

from aiogram import F, Router
from aiogram.types import Message

from telegram_bots.bots.fat_joke.services.reactions import StickerReplier, text_reactions

logger = logging.getLogger(__name__)
router = Router(name="reactions")
sticker_replier = StickerReplier()


async def send_reply(message: Message, reply):
    if reply.kind == "text":
        await message.answer(reply.value)
    elif reply.kind == "sticker":
        await message.answer_sticker(reply.value)
    elif reply.kind == "photo":
        await message.answer_photo(reply.value)
    elif reply.kind == "animation":
        await message.answer_animation(reply.value)


@router.message(F.text)
async def text_reply(message: Message):
    for reply in text_reactions(message.text):
        await send_reply(message, reply)


@router.message(F.sticker)
async def sticker_reply(message: Message):
    # file ids are logged to make adding new reactions easier
    logger.debug("sticker file_unique_id=%s file_id=%s", message.sticker.file_unique_id, message.sticker.file_id)
    reply = sticker_replier.reply_for(message.chat.id, message.sticker.file_unique_id)
    if reply:
        await send_reply(message, reply)


@router.message(F.photo)
async def photo_reply(message: Message):
    logger.debug("photo file_id=%s", message.photo[0].file_id)


@router.message(F.animation)
async def animation_reply(message: Message):
    logger.debug("animation file_id=%s", message.animation.file_id)
