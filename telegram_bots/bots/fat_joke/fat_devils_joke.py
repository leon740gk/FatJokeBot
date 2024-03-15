import logging
import threading

import schedule
import telebot

from telegram_bots.bots.fat_joke.activity_hadling_tools import ActivityHandler
from telegram_bots.db_sqlite.sqlitre_connection import DBConnection
from telegram_bots.knowledge_base.fat_joke.chat_data import billi_chat_id, test_004_chat_id
from telegram_bots.bots.fat_joke.periodic_tasks import message_timer, schedule_checker, test_your_brain, we_miss_you
from telegram_bots.knowledge_base.fat_joke.reaction_data import (
    sticker_responses,
    text_to_text_reactions,
    sticker_to_text_reactions,
    froggy_sticker,
    special_sticker_responses,
    photo_to_text_reactions,
    commands_responses,
    animation_to_text_reactions,
    genuis_sticker,
    smart_nigga,
    red_blink,
)
from telegram_bots.knowledge_base.fat_joke.l_podreviansjkyi.philosophy import bot_philosophy
from telegram_bots.bots.fat_joke.reaction_tools import (
    ToTextReactions,
    ToPhotoReactions,
    ToStickerReactions,
    CommandHandler,
)
from telegram_bots.bots.fat_joke.token_for_fat_joke import fat_joke_token
from telegram_bots.bots.fat_joke.iq_level_tools import (
    define_iq_levels,
    get_user_iq_and_name,
    calculate_id,
    change_iq,
    did_user_answer_this_question,
    get_anti_cheat_message,
    get_already_answered_questions,
    get_quiz_leaders,
)

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)

BOT_TOKEN = fat_joke_token
bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)
activity_handler = ActivityHandler(logger)


@bot.message_handler(commands=["help"])
def help(message):
    user_id = message.from_user.id
    activity_handler.update_user_activity_data(user_id, db)
    command_handler = CommandHandler(bot, message)
    command_handler.text_to_command(commands_responses.get("help"))


@bot.message_handler(commands=["already_answered_questions"])
def already_answered_questions(message):
    user_id = message.from_user.id
    answer = get_already_answered_questions(user_id, db)
    activity_handler.update_user_activity_data(user_id, db)
    command_handler = CommandHandler(bot, message)
    command_handler.text_to_command(answer)


@bot.message_handler(commands=["show_leaders"])
def show_leaders(message):
    user_id = message.from_user.id
    answer = get_quiz_leaders(db)
    activity_handler.update_user_activity_data(user_id, db)
    command_handler = CommandHandler(bot, message)
    command_handler.text_to_command(answer)


@bot.message_handler(commands=["show_iq"])
def show_iq(message):
    user_id = message.from_user.id
    activity_handler.update_user_activity_data(user_id, db)
    user_data_query = """
    SELECT name, IQ_level FROM Users
    """
    user_data = db.select_query(user_data_query)
    message_to_send = define_iq_levels(user_data)
    command_handler = CommandHandler(bot, message)
    command_handler.text_to_command(message_to_send)


@bot.message_handler(commands=["stream"])
def stream(message):
    user_id = message.from_user.id
    activity_handler.update_user_activity_data(user_id, db)
    command_handler = CommandHandler(bot, message)
    command_handler.text_to_command(commands_responses.get("stream"))


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.message:
        user_id = call.from_user.id
        activity_handler.update_user_activity_data(user_id, db)
        user_iq_old, user_name = get_user_iq_and_name(user_id, db)
        split_answer = call.data.split(" ")
        if len(split_answer) == 2:
            question_number = split_answer[1]
            logger.debug(
                f"answer from user_id --->>> {user_id} name --->>> {user_name}; question_number: {question_number}"
            )
            they_did = did_user_answer_this_question(user_id, question_number, db)
            if they_did:
                cheat_message = get_anti_cheat_message(user_name)
                bot.send_animation(call.message.chat.id, red_blink)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id, text=cheat_message)
                return
            else:
                user_iq_new, success_message = calculate_id(user_iq_old, user_name, increase=True)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id, text=success_message)
                bot.send_sticker(call.message.chat.id, smart_nigga)
        else:
            logger.debug(f"answer from user_id --->>> {user_id} name --->>> {user_name}")
            user_iq_new, fail_message = calculate_id(user_iq_old, user_name, increase=False)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id, text=fail_message)
            bot.send_sticker(call.message.chat.id, genuis_sticker)
        change_iq(user_id, user_iq_new, db)


@bot.message_handler(content_types=["text"])
def text_reply(message):
    user_id = message.from_user.id
    logger.debug(f"message from user_id --->>> {user_id} username --->>> {message.from_user.username}")
    activity_handler.update_user_activity_data(user_id, db)
    to_text_reaction = ToTextReactions(bot, message)
    to_text_reaction._text_to_text_reply(text_to_text_reactions)
    to_text_reaction._sticker_to_text_reply(sticker_to_text_reactions)
    to_text_reaction._photo_to_text_reply(photo_to_text_reactions)
    to_text_reaction._animation_to_text_reply(animation_to_text_reactions)
    to_text_reaction._bots_philosophy(bot_philosophy)


@bot.message_handler(content_types=["sticker"])
def sticker_reply(message):
    user_id = message.from_user.id
    logger.debug(f"Sticker From user_id --->>> {user_id} - {message.from_user.username}")
    logger.debug(f"Sticker file_unique_id --->>> {message.sticker.file_unique_id}")
    logger.debug(f"Sticker file_id --->>> {message.sticker.file_id}")
    activity_handler.update_user_activity_data(user_id, db)

    to_sticker_reaction = ToStickerReactions(bot, message)
    to_sticker_reaction._react_to_sticker(sticker_responses, special_sticker_responses)


@bot.message_handler(content_types=["photo"])
def photo_reply(message):
    user_id = message.from_user.id
    logger.debug(f"Photo From user_id --->>> {user_id} - {message.from_user.username}")
    logger.debug(f"file_id --->>> {message.json.get('photo')[0]['file_id']}")
    activity_handler.update_user_activity_data(user_id, db)

    to_photo_reaction = ToPhotoReactions(bot, message)
    to_photo_reaction._react_to_photo(froggy_sticker)


@bot.message_handler(content_types=["animation"])
def animation_reply(message):
    user_id = message.from_user.id
    logger.debug(f"animation From user_id --->>> {user_id} - {message.from_user.username}")
    logger.debug(f"file_id --->>> {message.document.file_id}")


if __name__ == "__main__":
    db = DBConnection()
    schedule.every(1).hour.at(":00").do(message_timer, bot=bot, chat_id=billi_chat_id)
    # schedule.every(15).minutes.do(test_your_brain, bot=bot, chat_id=billi_chat_id)
    schedule.every().day.at("14:55").do(activity_handler.check_daily_activity, db=db)
    schedule.every().day.at("15:00").do(we_miss_you, bot=bot, chat_id=billi_chat_id, db=db)
    threading.Thread(target=schedule_checker).start()
    bot.infinity_polling()
    db.close_connection()
