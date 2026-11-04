import random

from telegram_bots.engine.content import kb
from telegram_bots.engine.services.people import mention
from telegram_bots.engine.services.words import plural

SCAN_STEPS = 3


def scan_messages(winner, rng=random):
    """The "scanning" messages and the announcement of the fatty of the day."""
    name, username = winner
    steps = rng.sample(kb.fat_day_data.scan_phrases, SCAN_STEPS)
    return [*steps, rng.choice(kb.fat_day_data.winner_phrases).format(who=mention(name, username))]


def already_picked(winner, rng=random):
    return rng.choice(kb.fat_day_data.already_phrases).format(who=mention(*winner))


def times_word(count):
    return plural(count, *kb.texts.times_forms)


def format_stats(rows):
    if not rows:
        return kb.texts.fat_stats_empty
    medals = ["🥇", "🥈", "🥉"]
    lines = [kb.texts.fat_stats_title]
    for place, (name, days) in enumerate(rows):
        marker = medals[place] if place < len(medals) else f"{place + 1}."
        lines.append(f"{marker} {name} — {days} {times_word(days)}")
    return "\n".join(lines)
