import random

from telegram_bots.bots.fat_joke.services.people import mention


def find_author_quotes(quotes, author):
    """Quotes whose author's name or username contains `author`, case-insensitive."""
    needle = author.strip().lstrip("@").lower()
    return [quote for quote in quotes if needle in quote[1].lower() or needle in (quote[2] or "").lower()]


def pick(quotes, author=None, rng=random):
    if author:
        quotes = find_author_quotes(quotes, author)
    return rng.choice(quotes) if quotes else None


def format_quote(quote, title=None):
    text, author_name, author_username, said_on = quote
    year, month, day = said_on.split("-")
    lines = [title, ""] if title else []
    lines += [f"«{text}»", f"— {mention(author_name, author_username)}, {day}.{month}.{year}"]
    return "\n".join(lines)
