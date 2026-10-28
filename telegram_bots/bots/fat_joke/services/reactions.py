import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from telegram_bots.knowledge_base.fat_joke.l_podreviansjkyi.philosophy import bot_philosophy
from telegram_bots.knowledge_base.fat_joke.reaction_data import (
    animation_to_text_reactions,
    photo_to_text_reactions,
    special_sticker_responses,
    sticker_responses,
    sticker_to_text_reactions,
    text_to_text_reactions,
)

PHILOSOPHY_CHANCE = 1 / 11
STICKER_REPLY_CHANCE = 0.3
STICKER_REPLY_COOLDOWN = timedelta(minutes=5)


@dataclass(frozen=True)
class Reply:
    kind: str  # "text", "sticker", "photo" or "animation"
    value: str


def _pick(value, rng):
    return rng.choice(value) if isinstance(value, list) else value


def _matches(text, mapper, kind, rng):
    # one reply per keyword group, even if several keywords of the group are in the text
    return [
        Reply(kind, _pick(reply, rng))
        for keywords, reply in mapper.items()
        if any(keyword.lower() in text for keyword in keywords)
    ]


def text_reactions(text, rng=random):
    text = text.lower()
    replies = (
        _matches(text, text_to_text_reactions, "text", rng)
        + _matches(text, sticker_to_text_reactions, "sticker", rng)
        + _matches(text, photo_to_text_reactions, "photo", rng)
        + _matches(text, animation_to_text_reactions, "animation", rng)
    )
    if rng.random() < PHILOSOPHY_CHANCE:
        replies.append(Reply("text", rng.choice(bot_philosophy)))
    return replies


class StickerReplier:
    """Answers special stickers every time, other stickers only now and then."""

    def __init__(self, chance=STICKER_REPLY_CHANCE, cooldown=STICKER_REPLY_COOLDOWN, rng=random):
        self.chance = chance
        self.cooldown = cooldown
        self.rng = rng
        self.last_reply_at = {}

    def reply_for(self, chat_id, sticker_unique_id, now=None):
        if sticker_unique_id in special_sticker_responses:
            return Reply("text", self.rng.choice(special_sticker_responses[sticker_unique_id]))

        now = now or datetime.now()
        last_reply_at = self.last_reply_at.get(chat_id)
        if last_reply_at and now - last_reply_at < self.cooldown:
            return None
        if self.rng.random() >= self.chance:
            return None
        self.last_reply_at[chat_id] = now
        return Reply("text", self.rng.choice(sticker_responses))
