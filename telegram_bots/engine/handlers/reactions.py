import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, ReactionTypeEmoji

from telegram_bots.engine.services.chat_games import Reactor
from telegram_bots.engine.services.reactions import StickerReplier, text_reactions

logger = logging.getLogger(__name__)
router = Router(name="reactions")
sticker_replier = StickerReplier()
reactor = Reactor()


async def send_reply(message: Message, reply):
    if reply.kind == "text":
        await message.answer(reply.value)
    elif reply.kind == "sticker":
        await message.answer_sticker(reply.value)
    elif reply.kind == "photo":
        await message.answer_photo(reply.value)
    elif reply.kind == "animation":
        await message.answer_animation(reply.value)


async def maybe_react(message: Message, settings):
    """Now and then a reaction from the bot on an ordinary message: someone noticed it."""
    if not settings.reactions_enabled or message.chat.type == ChatType.PRIVATE:
        return
    emoji = reactor.pick(message.chat.id)
    if not emoji:
        return
    try:
        await message.react([ReactionTypeEmoji(emoji=emoji)])
    except TelegramAPIError as error:
        # the chat may allow only some reactions
        logger.debug("can't react with %s in chat %s: %s", emoji, message.chat.id, error.message)


@router.message(F.text)
async def text_reply(message: Message, settings):
    for reply in text_reactions(message.text):
        await send_reply(message, reply)
    await maybe_react(message, settings)


@router.message(F.sticker)
async def sticker_reply(message: Message):
    # file ids are logged to make adding new reactions easier
    logger.debug("sticker file_unique_id=%s file_id=%s", message.sticker.file_unique_id, message.sticker.file_id)
    reply = sticker_replier.reply_for(message.chat.id, message.sticker.file_unique_id)
    if reply:
        await send_reply(message, reply)


@router.message(F.photo)
async def photo_reply(message: Message):
    logger.debug("photo file_id=%s", message.photo[-1].file_id)


@router.message(F.animation)
async def animation_reply(message: Message):
    logger.debug("animation file_id=%s", message.animation.file_id)
