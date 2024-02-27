import datetime
import random
from time import sleep

import pytz
import schedule
from telebot import types

from telegram_bots.knowledge_base.fat_joke.reaction_data import wanted
from telegram_bots.knowledge_base.fat_joke.test_your_mind.ukr_language.qa_data import questionnaire
from telegram_bots.knowledge_base.fat_joke.timer_data import time_mapper


def schedule_checker():
    while True:
        schedule.run_pending()
        sleep(59)


def message_timer(bot, chat_id):
    time_now = datetime.datetime.now(pytz.timezone("Europe/Kiev")).strftime("%H")
    bot.send_message(chat_id, text=f"{time_mapper.get(time_now)} блеать! Можна на годинник не дивицця!")


def test_your_brain(bot, chat_id):
    category = "Українська мова.\n"
    pick_random_question = random.randint(1, len(questionnaire))
    question_dict = questionnaire.get(pick_random_question)
    question = list(question_dict.keys())[0]
    answers_dict = question_dict.get(question)

    markup = types.InlineKeyboardMarkup(row_width=2)
    answer_1 = types.InlineKeyboardButton(text=answers_dict.get("1")[0], callback_data=answers_dict.get("1")[1])
    answer_2 = types.InlineKeyboardButton(text=answers_dict.get("2")[0], callback_data=answers_dict.get("2")[1])
    answer_3 = types.InlineKeyboardButton(text=answers_dict.get("3")[0], callback_data=answers_dict.get("3")[1])
    answer_4 = types.InlineKeyboardButton(text=answers_dict.get("4")[0], callback_data=answers_dict.get("4")[1])
    q_text_plus_category = category + question
    markup.add(answer_1, answer_2, answer_3, answer_4)
    bot.send_message(chat_id, text=q_text_plus_category, reply_markup=markup)


def we_miss_you(bot, chat_id, db):
    activity_query = """
    SELECT name, username, activity_delta FROM Users WHERE activity_delta > 0
    """
    strings_to_join = ["Увага! Увага!\nНаш бот розшукує пропавших без вісти!\n"]
    result = db.select_query(activity_query)
    if result:
        for user_data in result:
            days = define_days_word(user_data[2])
            miss_you_string = f"{user_data[0]} @{user_data[1]}, про тебе ми не чули вже {user_data[2]} {days} :(\n"
            strings_to_join.append(miss_you_string)
        strings_to_join.append("Бот і Сірожка сумують за вами...\nНапишіть як у вас справи.\nЧекаємо на вас :)")
        miss_you_message = "".join(strings_to_join)
        bot.send_message(chat_id, miss_you_message)
        bot.send_sticker(chat_id, wanted)


def define_days_word(days: int):
    days_str = str(days)
    if days_str in ["11", "12", "13", "14"]:
        return "днів"
    if days_str.endswith("1"):
        return "день"
    elif days_str.endswith("2") or days_str.endswith("3") or days_str.endswith("4"):
        return "дні"
    else:
        return "днів"
