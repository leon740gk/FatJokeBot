import datetime
import random
from time import sleep

import pytz
import schedule
from telebot import types

from telegram_bots.knowledge_base.fat_joke.reaction_data import wanted
from telegram_bots.knowledge_base.fat_joke.test_your_mind.ukr_language.qa_data import questionnaire as ukr_lang_q
from telegram_bots.knowledge_base.fat_joke.test_your_mind.geography.qa_data import questionnaire as geo_q
from telegram_bots.knowledge_base.fat_joke.test_your_mind.biology.qa_data import questionnaire as bio_q
from telegram_bots.knowledge_base.fat_joke.test_your_mind.new_qa.qa_data import questionnaire as general_q
from telegram_bots.knowledge_base.fat_joke.test_your_mind.mlbb.qa_data import questionnaire as mlbb_q
from telegram_bots.knowledge_base.fat_joke.timer_data import time_mapper


UKR_LANG = "Українська мова.\n"
GEOGRAPHY = "Географія. \n"
BIOLOGY = "Біологія. \n"
GENERAL = "Мікс питань. \n"
MLBB = "MLBB. \n"
q_mapper = {UKR_LANG: ukr_lang_q, GEOGRAPHY: geo_q, BIOLOGY: bio_q, GENERAL: general_q, MLBB: mlbb_q}
# short codes go into callback_data, so question numbers from different disciplines don't collide
discipline_codes = {UKR_LANG: "ukr", GEOGRAPHY: "geo", BIOLOGY: "bio", GENERAL: "mix", MLBB: "mlbb"}
CURRENT_DISCIPLINE = MLBB
CURRENT_DISCIPLINE_CODE = discipline_codes[CURRENT_DISCIPLINE]


def make_answer_callback_data(question_number, answer):
    is_correct = 1 if answer[1].startswith("correct") else 0
    return f"q {CURRENT_DISCIPLINE_CODE} {question_number} {is_correct}"


def schedule_checker():
    while True:
        schedule.run_pending()
        sleep(59)


def message_timer(bot, chat_id):
    time_now = datetime.datetime.now(pytz.timezone("Europe/Kiev")).strftime("%H")
    bot.send_message(chat_id, text=f"Бам!!!\n{time_mapper.get(time_now)} блеать! Можна на годинник не дивицця!")


def test_your_brain(bot, chat_id):
    category = CURRENT_DISCIPLINE
    questions = q_mapper.get(category)
    pick_random_question = random.randint(1, len(questions))
    question_dict = questions.get(pick_random_question)
    question = list(question_dict.keys())[0]
    answers_dict = question_dict.get(question)

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(
            text=answers_dict.get(key)[0],
            callback_data=make_answer_callback_data(pick_random_question, answers_dict.get(key)),
        )
        for key in ["1", "2", "3", "4"]
    ]
    q_text_plus_category = category + question
    markup.add(*buttons)
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
