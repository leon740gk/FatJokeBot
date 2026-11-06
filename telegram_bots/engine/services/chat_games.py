"""Small things that make a shy chat talk: polls, the question of the day, riddles and reactions from the bot.

Their content is knowledge_base/<bot>/chat_games_data.py; an empty list there turns the game off for that bot.
"""

import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from telegram_bots.engine.content import kb

# a riddle gets a hint every HINT_MINUTES, and after the last hint one more period passes before the answer
HINT_MINUTES = 30
# XP for a riddle by the number of hints shown before it was solved
RIDDLE_POINTS = (15, 10, 5)
DAILY_ANSWER_POINTS = 3
# the bot puts a reaction on an ordinary message now and then, not more often than once per cooldown in a chat
REACTION_CHANCE = 0.07
REACTION_COOLDOWN = timedelta(minutes=20)
ANON_DAILY_LIMIT = 3
ANON_MAX_LENGTH = 1000


@dataclass(frozen=True)
class Riddle:
    clue: str
    hints: tuple
    answers: tuple  # the first one is shown when the riddle is over


def pick_fresh(count, used, rng=random):
    """Number of an item not used in this chat yet; when all have been used, they go round again."""
    fresh = [number for number in range(count) if number not in used]
    return rng.choice(fresh or range(count))


def riddles():
    return [Riddle(clue, tuple(hints), tuple(answers)) for clue, hints, answers in kb.chat_games_data.riddles]


def get_riddle(number):
    items = riddles()
    return items[number] if 0 <= number < len(items) else None


def normalize(text):
    """Lower case, letters and digits only, so "The Witcher 3!" and "the witcher 3" are the same answer."""
    text = re.sub(r"['’ʼ`]", "", text.lower().replace("ё", "е"))
    return " ".join(re.findall(r"\w+", text))


def is_answer(text, riddle):
    """The answer may be the whole message or a part of it: "це ж Minecraft" counts."""
    message = f" {normalize(text)} "
    return any(f" {normalize(answer)} " in message for answer in riddle.answers if normalize(answer))


def riddle_points(hints_shown):
    return RIDDLE_POINTS[min(hints_shown, len(RIDDLE_POINTS) - 1)]


def hints_due(riddle, started_at, now):
    """How many hints should be out by now."""
    return min(int((now - started_at) // (HINT_MINUTES * 60)), len(riddle.hints))


def is_over(riddle, started_at, now):
    return now - started_at >= (len(riddle.hints) + 1) * HINT_MINUTES * 60


def riddle_text(riddle):
    return kb.texts.riddle_start.format(riddle=riddle.clue, points=riddle_points(0), xp=kb.theme_data.points)


def hint_text(riddle, number):
    """number counts from 1."""
    return kb.texts.riddle_hint.format(
        number=number, hint=riddle.hints[number - 1], points=riddle_points(number), xp=kb.theme_data.points
    )


def daily_question_text(number):
    return kb.texts.daily_question.format(
        question=kb.chat_games_data.daily_questions[number], points=DAILY_ANSWER_POINTS, xp=kb.theme_data.points
    )


class Reactor:
    """Picks a reaction for an ordinary message now and then, at most once per cooldown in a chat."""

    def __init__(self, chance=None, cooldown=REACTION_COOLDOWN, rng=random):
        self.chance = chance
        self.cooldown = cooldown
        self.rng = rng
        self.last_at = {}

    def pick(self, chat_id, now=None):
        emojis = kb.reaction_data.message_reactions
        if not emojis:
            return None
        now = now or datetime.now()
        last_at = self.last_at.get(chat_id)
        if last_at and now - last_at < self.cooldown:
            return None
        chance = REACTION_CHANCE if self.chance is None else self.chance
        if self.rng.random() >= chance:
            return None
        self.last_at[chat_id] = now
        return self.rng.choice(emojis)
