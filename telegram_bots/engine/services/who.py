import random

from aiogram.types import User
from aiogram.utils.formatting import Text, TextMention

from telegram_bots.engine.content import kb
from telegram_bots.engine.services.people import mention
from telegram_bots.engine.services.words import plural

# a Telegram poll takes 2 to 10 options
MIN_OPTIONS = 2
MAX_OPTIONS = 10
POLL_HOURS = 3


def pick_question(used, rng=random):
    """A question not asked in this chat yet; when all have been asked, they go round again."""
    prefix, questions = kb.who_data.prefix, kb.who_data.who_questions
    fresh = [question for question in questions if prefix + question not in used]
    return prefix + rng.choice(fresh or questions)


def pick_options(members, rng=random):
    """(telegram_id, name, username) of up to 10 members, shuffled; None if there are fewer than two."""
    if len(members) < MIN_OPTIONS:
        return None
    return rng.sample(list(members), min(len(members), MAX_OPTIONS))


def option_labels(options):
    """Names on the poll; a username tells apart people with the same name."""
    names = [name for _, name, _ in options]
    return [mention(name, username) if names.count(name) > 1 else name for _, name, username in options]


def result(question, options, counts):
    """Announcement of who got the most votes, with a real mention of each winner."""
    best = max(counts, default=0)
    if not best:
        return Text(kb.texts.who_no_votes.format(question=question))
    winners = [option for option, count in zip(options, counts, strict=False) if count == best]
    parts = [kb.texts.who_result.format(question=question)]
    for index, (user_id, name, _) in enumerate(winners):
        if index:
            parts.append(kb.texts.who_and)
        parts.append(TextMention(name, user=User(id=user_id, is_bot=False, first_name=name)))
    votes = plural(best, *kb.texts.vote_forms)
    parts.append(f"! {best} {votes}" + (kb.texts.who_shared if len(winners) > 1 else " 🏆"))
    return Text(*parts)
