import logging

import telebot

from telegram_bots.reaction_data import (
    sticker_responses,
    text_to_text_reactions,
    sticker_to_text_reactions,
    froggy_sticker,
    special_sticker_responses,
    photo_to_text_reactions,
)
from telegram_bots.knowledge_base.l_podreviansjkyi.philosophy import bot_philosophy
from telegram_bots.reaction_tools import ToTextReactions, ToPhotoReactions, ToStickerReactions
from telegram_bots.token import fat_joke_token

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)

BOT_TOKEN = fat_joke_token
bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)


@bot.message_handler(content_types=["text"])
def text_reply(message):
    to_text_reaction = ToTextReactions(bot, message)
    to_text_reaction._text_to_text_reply(text_to_text_reactions)
    to_text_reaction._sticker_to_text_reply(sticker_to_text_reactions)
    to_text_reaction._photo_to_text_reply(photo_to_text_reactions)
    to_text_reaction._bots_philosophy(bot_philosophy)


@bot.message_handler(content_types=["sticker"])
def sticker_reply(message):
    logger.debug(f"Sticker From user_id --->>> {message.from_user.id} - {message.from_user.username}")
    logger.debug(f"Sticker file_unique_id --->>> {message.sticker.file_unique_id}")
    logger.debug(f"Sticker file_id --->>> {message.sticker.file_id}")

    to_sticker_reaction = ToStickerReactions(bot, message)
    to_sticker_reaction._react_to_sticker(sticker_responses, special_sticker_responses)


@bot.message_handler(content_types=["photo"])
def photo_reply(message):
    logger.debug(f"Photo From user_id --->>> {message.from_user.id} - {message.from_user.username}")
    logger.debug(f"file_id --->>> {message.json.get('photo')[0]['file_id']}")

    to_photo_reaction = ToPhotoReactions(bot, message)
    to_photo_reaction._react_to_photo(froggy_sticker)


if __name__ == "__main__":
    bot.infinity_polling()
