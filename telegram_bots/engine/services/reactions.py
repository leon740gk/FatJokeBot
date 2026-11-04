import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from telegram_bots.engine.content import kb

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
        _matches(text, kb.reaction_data.text_to_text_reactions, "text", rng)
        + _matches(text, kb.reaction_data.sticker_to_text_reactions, "sticker", rng)
        + _matches(text, kb.reaction_data.photo_to_text_reactions, "photo", rng)
        + _matches(text, kb.reaction_data.animation_to_text_reactions, "animation", rng)
    )
    if rng.random() < PHILOSOPHY_CHANCE:
        replies.append(Reply("text", rng.choice(rng.choice(kb.random_phrases.random_phrase_groups))))
    return replies


class StickerReplier:
    """Answers special stickers every time, other stickers only now and then."""

    def __init__(self, chance=STICKER_REPLY_CHANCE, cooldown=STICKER_REPLY_COOLDOWN, rng=random):
        self.chance = chance
        self.cooldown = cooldown
        self.rng = rng
        self.last_reply_at = {}

    def reply_for(self, chat_id, sticker_unique_id, now=None):
        special = kb.reaction_data.special_sticker_responses
        if sticker_unique_id in special:
            return Reply("text", self.rng.choice(special[sticker_unique_id]))

        now = now or datetime.now()
        last_reply_at = self.last_reply_at.get(chat_id)
        if last_reply_at and now - last_reply_at < self.cooldown:
            return None
        if self.rng.random() >= self.chance:
            return None
        self.last_reply_at[chat_id] = now
        return Reply("text", self.rng.choice(kb.reaction_data.sticker_responses))
