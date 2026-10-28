from telegram_bots.knowledge_base.fat_joke.timer_data import time_mapper


def hour_message(hour):
    return f"Бам!!!\n{time_mapper.get(hour)} блеать! Можна на годинник не дивицця!"


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
