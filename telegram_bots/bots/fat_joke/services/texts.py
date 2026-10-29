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
    for flag, country, country_hour in (("🇺🇦", "ua", hour), ("🇩🇪", "de", germany_hour)):
        phrase = rng.choice(hour_phrases[country][day_part(int(country_hour))])
        lines.append(f"{flag} {country_hour}:00 - час {phrase}!")
    return "\n".join(lines)


def days_word(days):
    if 11 <= days % 100 <= 14:
        return "днів"
    if days % 10 == 1:
        return "день"
    if days % 10 in (2, 3, 4):
        return "дні"
    return "днів"


def miss_you_message(inactive_users):
    if not inactive_users:
        return None
    lines = ["Увага! Увага!\nНаш бот розшукує пропавших без вісти!\n"]
    for name, username, days in inactive_users:
        lines.append(f"{name} @{username}, про тебе ми не чули вже {days} {days_word(days)} :(\n")
    lines.append("Бот і Сірожка сумують за вами...\nНапишіть як у вас справи.\nЧекаємо на вас :)")
    return "".join(lines)
