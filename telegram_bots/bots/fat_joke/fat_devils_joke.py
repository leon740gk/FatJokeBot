import logging
import threading

import schedule
import telebot

from telegram_bots.db_sqlite.sqlitre_connection import DBConnection
from telegram_bots.knowledge_base.fat_joke.chat_data import billi_chat_id
from telegram_bots.knowledge_base.fat_joke.periodic_tasks import message_timer, schedule_checker, test_your_brain
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
from telegram_bots.knowledge_base.fat_joke.test_your_mind.iq_level_data import define_iq_levels, iq_level_mapper

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)

BOT_TOKEN = fat_joke_token
bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)


@bot.message_handler(commands=["help"])
def help(message):
    command_handler = CommandHandler(bot, message)
    command_handler.text_to_command(commands_responses.get("help"))


@bot.message_handler(commands=["show_iq"])
def show_iq(message):
    user_data_query = """
    SELECT name, IQ_level FROM Users
    """
    user_data = db.select_query(user_data_query)
    message_to_send = define_iq_levels(user_data, iq_level_mapper)
    command_handler = CommandHandler(bot, message)
    command_handler.text_to_command(message_to_send)


@bot.message_handler(commands=["stream"])
def stream(message):
    command_handler = CommandHandler(bot, message)
    command_handler.text_to_command(commands_responses.get("stream"))


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.message:
        user_id = call.from_user.id
        select_query_iq_level = f"""
            SELECT iq_level, name FROM Users WHERE telegram_id = {user_id}
        """
        results = db.select_query(select_query_iq_level)
        user_iq_old = results[0][0]
        user_name = results[0][1]
        if call.data == "correct":
            user_iq_new = user_iq_old + 1
            success_message = f"""
            Твій рівень IQ підріс з {user_iq_old} до {user_iq_new}!
{user_name} розумнішає! 
Ай молодчинка :)
            """
            bot.edit_message_text(
                chat_id=call.message.chat.id, message_id=call.message.id, text=success_message
            )
            bot.send_sticker(call.message.chat.id, raund)
        else:
            user_iq_new = user_iq_old - 1
            fail_message = f"""
            Твій рівень IQ впав з {user_iq_old} до {user_iq_new}!
Ой-ой, {user_name} потроху тупіє :( 
Будеш ням-ням дімідрольчик?
            """
            bot.edit_message_text(
                chat_id=call.message.chat.id, message_id=call.message.id, text=fail_message
            )
            bot.send_sticker(call.message.chat.id, dick)
        commit_query_iq_level = f"""
            UPDATE Users SET iq_level = {user_iq_new} WHERE telegram_id = {user_id}
        """
        db.commit_query(commit_query_iq_level)


@bot.message_handler(content_types=["text"])
def text_reply(message):
    logger.debug(f"Chat id --->>> {message.chat.id}")
    logger.debug(f"user_id --->>> {message.from_user.id}")

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
    db = DBConnection()
    schedule.every(1).hour.at(":00").do(message_timer, bot=bot, chat_id=billi_chat_id)
    schedule.every(5).minutes.do(test_your_brain, bot=bot, chat_id=billi_chat_id)
    threading.Thread(target=schedule_checker).start()
    bot.infinity_polling()
    db.close_connection()
