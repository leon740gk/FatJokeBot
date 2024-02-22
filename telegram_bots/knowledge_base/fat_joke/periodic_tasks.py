import datetime
from time import sleep

import pytz
import schedule


def schedule_checker():
    while True:
        schedule.run_pending()
        sleep(59)


def message_timer(bot, chat_id, time_mapper):
    time_now = datetime.datetime.now(pytz.timezone("Europe/Kiev")).strftime("%H")
    bot.send_message(chat_id, text=f"{time_mapper.get(time_now)} блеать! Можна на годинник не дивицця!")
