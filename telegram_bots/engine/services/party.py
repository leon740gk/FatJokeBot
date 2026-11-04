from aiogram.types import User
from aiogram.utils.formatting import Text, TextMention

from telegram_bots.engine.content import kb

# /party 3 gathers three people, a plain /party five
PARTY_SIZES = (2, 3, 5)
DEFAULT_SIZE = 5
# a party that hasn't gathered in this many minutes is dead, its buttons stop working
PARTY_MINUTES = 30
JOIN = "party in"
LEAVE = "party out"


def parse_args(args):
    """(size, comment) from the text after /party: a leading 2, 3 or 5 is the size."""
    first, _, rest = (args or "").strip().partition(" ")
    if first.isdigit() and int(first) in PARTY_SIZES:
        return int(first), rest.strip()
    return DEFAULT_SIZE, (args or "").strip()


def party_text(comment, members, size, expired=False):
    lines = [kb.texts.party_title]
    if comment:
        lines.append(comment)
    lines.append(kb.texts.party_count.format(count=len(members), size=size))
    for number, (_, name, username) in enumerate(members, start=1):
        lines.append(f"{number}. {name}" + (f" (@{username})" if username else ""))
    if len(members) >= size:
        lines.append(kb.texts.party_gathered)
    elif expired:
        lines.append(kb.texts.party_expired.format(minutes=PARTY_MINUTES))
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
