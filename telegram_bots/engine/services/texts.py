import random
from zoneinfo import ZoneInfo

from telegram_bots.engine.content import kb
from telegram_bots.engine.services.words import plural


def day_part(hour):
    if hour < 6:
        return "night"
    if hour < 12:
        return "morning"
    if hour < 18:
        return "day"
    return "evening"


def hour_message(now, rng=random):
    """The "Бам" with a line per clock of the bot (timer_data.clocks), each with a phrase for its part of the day."""
    lines = [kb.timer_data.bam_title]
    for flag, time_zone, time_word, phrases in kb.timer_data.clocks:
        hour = now.astimezone(ZoneInfo(time_zone)).hour
        phrase = rng.choice(phrases[day_part(hour)])
        lines.append(f"{flag} {hour:02d}:00 - {time_word} {phrase}!")
    return "\n".join(lines)


def days_word(days):
    return plural(days, *kb.texts.day_forms)


def miss_you_message(inactive_users):
    if not inactive_users:
        return None
    lines = [kb.texts.miss_you_title]
    for name, username, days in inactive_users:
        lines.append(kb.texts.miss_you_row.format(name=name, username=username, days=days, days_word=days_word(days)))
    lines.append(kb.texts.miss_you_footer)
    return "".join(lines)
