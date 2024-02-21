import datetime
import logging
import threading
import time

import pytz
import telebot

from telegram_bots.knowledge_base.chat_data import billi_chat_id
from telegram_bots.knowledge_base.timer_data import time_mapper
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
    logger.debug(f"Chat id --->>> {message.chat.id}")

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

def message_timer():
    first_run = True
    while True:
        minutes = datetime.datetime.now(pytz.timezone('Europe/Kiev')).strftime('%M')
        if first_run and minutes != '00':
            time_to_sleep = 60 - int(minutes) - 1
            time.sleep(time_to_sleep)
        if minutes == '00':
            first_run = False
            time_now = datetime.datetime.now(pytz.timezone('Europe/Kiev')).strftime('%H')
            bot.send_message(billi_chat_id, text=f"{time_mapper.get(time_now)} блеать! Можна на годинник не дивицця!")
            time.sleep(59)


x = threading.Thread(target=message_timer)
x.start()


if __name__ == "__main__":
    bot.infinity_polling()

