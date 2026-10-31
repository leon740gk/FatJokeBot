import random

from telegram_bots.knowledge_base.fat_joke.timer_data import hour_phrases


def day_part(hour):
    if hour < 6:
        return "night"
    if hour < 12:
        return "morning"
    if hour < 18:
        return "day"
    return "evening"


def hour_message(hour, germany_hour, rng=random):
    """Hours are "HH" strings, each country gets a "time to ..." phrase for its own part of the day."""
    lines = ["Бам!!! Говорит Омниссия!"]
    # Ukraine keeps its Ukrainian "час ...", the rest of the bot speaks Russian
    for flag, country, country_hour, time_word in (("🇺🇦", "ua", hour, "час"), ("🇩🇪", "de", germany_hour, "время")):
        phrase = rng.choice(hour_phrases[country][day_part(int(country_hour))])
        lines.append(f"{flag} {country_hour}:00 - {time_word} {phrase}!")
    return "\n".join(lines)


def days_word(days):
    if 11 <= days % 100 <= 14:
        return "дней"
    if days % 10 == 1:
        return "день"
    if days % 10 in (2, 3, 4):
        return "дня"
    return "дней"


def miss_you_message(inactive_users):
    if not inactive_users:
        return None
    lines = ["Внимание! Внимание!\nНаш бот разыскивает пропавших без вести!\n"]
    for name, username, days in inactive_users:
        lines.append(f"{name} @{username}, о тебе мы не слышали уже {days} {days_word(days)} :(\n")
    lines.append("Бот и весь чат скучают по вам...\nНапишите, как у вас дела.\nЖдём вас :)")
    return "".join(lines)
