import random

from telegram_bots.bots.fat_joke.services.people import mention
from telegram_bots.knowledge_base.fat_joke.fat_day_data import already_phrases, scan_phrases, winner_phrases

SCAN_STEPS = 3


def scan_messages(winner, rng=random):
    """The "scanning" messages and the announcement of the fatty of the day."""
    name, username = winner
    steps = rng.sample(scan_phrases, SCAN_STEPS)
    return [*steps, rng.choice(winner_phrases).format(who=mention(name, username))]


def already_picked(winner, rng=random):
    return rng.choice(already_phrases).format(who=mention(*winner))


def times_word(count):
    if 11 <= count % 100 <= 14:
        return "раз"
    if count % 10 in (2, 3, 4):
        return "раза"
    return "раз"


def format_stats(rows):
    if not rows:
        return "Жиртрестов ещё не было. Исправим: /fat 🍩"
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🍔 Зал славы жиртрестов:\n"]
    for place, (name, days) in enumerate(rows):
        marker = medals[place] if place < len(medals) else f"{place + 1}."
        lines.append(f"{marker} {name} — {days} {times_word(days)}")
    return "\n".join(lines)
