import logging
import threading

import schedule
import telebot
from telebot import types

from telegram_bots.knowledge_base.fat_joke.chat_data import billi_chat_id
from telegram_bots.knowledge_base.fat_joke.periodic_tasks import message_timer, schedule_checker
from telegram_bots.knowledge_base.fat_joke.timer_data import time_mapper
from telegram_bots.knowledge_base.fat_joke.reaction_data import (
    sticker_responses,
    text_to_text_reactions,
    sticker_to_text_reactions,
    froggy_sticker,
    special_sticker_responses,
    photo_to_text_reactions,
    commands_responses,
    dick,
    raund,
)
from telegram_bots.knowledge_base.fat_joke.l_podreviansjkyi.philosophy import bot_philosophy
from telegram_bots.bots.fat_joke.reaction_tools import (
    ToTextReactions,
    ToPhotoReactions,
    ToStickerReactions,
    CommandHandler,
)
from telegram_bots.bots.fat_joke.token import fat_joke_token

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)

BOT_TOKEN = fat_joke_token
bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)


@bot.message_handler(commands=["help"])
def help(message):
    logger.debug(f"message --->>> {message.from_user.id} - {message}")
    command_handler = CommandHandler(bot, message)
    command_handler.text_to_command(commands_responses.get("help"))


@bot.message_handler(commands=["test_your_brain"])
def test_your_brain(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    answer_1 = types.InlineKeyboardButton("Бот", callback_data="answer_1")
    answer_2 = types.InlineKeyboardButton("Санечек :)", callback_data="answer_2")
    answer_3 = types.InlineKeyboardButton("Сірожка", callback_data="answer_3")
    answer_4 = types.InlineKeyboardButton("Всі прям генії!", callback_data="answer_4")

    markup.add(answer_1, answer_2, answer_3, answer_4)
    bot.send_message(message.chat.id, "Хто найрозумніший в чаті?", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.message:
        if call.data == "answer_4":
            bot.edit_message_text(
                chat_id=call.message.chat.id, message_id=call.message.id, text="Таки так! Візьми з полки пиріжок"
            )
            bot.send_sticker(call.message.chat.id, raund)
        else:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id, text="Лузер йоба )")
            bot.send_sticker(call.message.chat.id, dick)


@bot.message_handler(content_types=["text"])
def text_reply(message):
    logger.debug(f"Chat id --->>> {message.chat.id}")
    logger.debug(f"file_id --->>> {message}")

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
    schedule.every(1).hour.at(":00").do(message_timer, bot=bot, chat_id=billi_chat_id, time_mapper=time_mapper)
    threading.Thread(target=schedule_checker).start()
    bot.infinity_polling()
