from aiogram.types import User
from aiogram.utils.formatting import Text, TextMention

from telegram_bots.engine.content import kb

PARTY_SIZE = 5
# a party that hasn't gathered in this many hours is dead, its buttons stop working
PARTY_HOURS = 3
JOIN = "party in"
LEAVE = "party out"


def party_text(comment, members, expired=False):
    lines = [kb.texts.party_title]
    if comment:
        lines.append(comment)
    lines.append(kb.texts.party_count.format(count=len(members), size=PARTY_SIZE))
    for number, (_, name, username) in enumerate(members, start=1):
        lines.append(f"{number}. {name}" + (f" (@{username})" if username else ""))
    if len(members) >= PARTY_SIZE:
        lines.append(kb.texts.party_gathered)
    elif expired:
        lines.append(kb.texts.party_expired.format(hours=PARTY_HOURS))
    else:
        lines.append(kb.texts.party_join_hint)
    return "\n".join(lines)


def gathered_call(members):
    """Pings everyone in the party, with a real mention even for people without a username."""
    parts = ["🔔 "]
    for index, (user_id, name, _) in enumerate(members):
        if index:
            parts.append(", ")
        parts.append(TextMention(name, user=User(id=user_id, is_bot=False, first_name=name)))
    parts.append(kb.texts.party_call)
    return Text(*parts)
