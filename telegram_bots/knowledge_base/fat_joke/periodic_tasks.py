import datetime
import random
from time import sleep

import pytz
import schedule
from telebot import types

from telegram_bots.knowledge_base.fat_joke.test_your_mind.qa_data import questionnaire
from telegram_bots.knowledge_base.fat_joke.timer_data import time_mapper


def schedule_checker():
    while True:
        schedule.run_pending()
        sleep(59)


def message_timer(bot, chat_id):
    time_now = datetime.datetime.now(pytz.timezone("Europe/Kiev")).strftime("%H")
    bot.send_message(chat_id, text=f"{time_mapper.get(time_now)} блеать! Можна на годинник не дивицця!")


def test_your_brain(bot, chat_id):
    pick_random_question = random.randint(1, len(questionnaire))
    question_dict = questionnaire.get(pick_random_question)
    question = list(question_dict.keys())[0]
    answers_dict = question_dict.get(question)

    markup = types.InlineKeyboardMarkup(row_width=2)
    answer_1 = types.InlineKeyboardButton(text=answers_dict.get("1")[0], callback_data=answers_dict.get("1")[1])
    answer_2 = types.InlineKeyboardButton(text=answers_dict.get("2")[0], callback_data=answers_dict.get("2")[1])
    answer_3 = types.InlineKeyboardButton(text=answers_dict.get("3")[0], callback_data=answers_dict.get("3")[1])
    answer_4 = types.InlineKeyboardButton(text=answers_dict.get("4")[0], callback_data=answers_dict.get("4")[1])

    markup.add(answer_1, answer_2, answer_3, answer_4)
    bot.send_message(chat_id, text=question, reply_markup=markup)
