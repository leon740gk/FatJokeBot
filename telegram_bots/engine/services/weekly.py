from collections import Counter
from dataclasses import dataclass
from datetime import timedelta

from telegram_bots.engine.content import kb
from telegram_bots.engine.db import weekly as weekly_db
from telegram_bots.engine.services.achievements import ACHIEVEMENT_BP
from telegram_bots.engine.services.fat_day import times_word
from telegram_bots.engine.services.people import mention
from telegram_bots.engine.services.quotes import format_quote
from telegram_bots.engine.services.words import plural

MEDALS = ["🥇", "🥈", "🥉"]
TOP = 3


@dataclass(frozen=True)
class Week:
    first_day: object  # date
    last_day: object
    messages: list  # (name, count)
    silent: list  # (name, username)
    correct_answers: list  # (name, count)
    loot: list  # (name, BP, times the top loot was taken, Lords in MLBB)
    fat_days: list  # (name, days)
    achievements: list  # (name, code)
    parties: int
    quote: tuple | None


def collect(db, chat_id, today):
    """The last 7 days up to `today` (a Kyiv date) in the chat."""
    first_day = today - timedelta(days=6)
    since = first_day.isoformat()
    return Week(
        first_day=first_day,
        last_day=today,
        messages=weekly_db.messages(db, chat_id, since),
        silent=weekly_db.silent(db, chat_id, since),
        correct_answers=weekly_db.correct_answers(db),
        loot=weekly_db.loot_points(db, chat_id),
        fat_days=weekly_db.fat_days(db, chat_id, since),
        achievements=weekly_db.achievements(db),
        parties=weekly_db.gathered_parties(db, chat_id),
        quote=weekly_db.random_quote(db, chat_id),
    )


def mvp(week):
    """Who did the most: a point per 10 messages, 3 per right answer, the loot BP and the achievement BP."""
    scores = Counter()
    for name, count in week.messages:
        scores[name] += count // 10
    for name, count in week.correct_answers:
        scores[name] += 3 * count
    for name, points, _ in week.loot:
        scores[name] += points
    for name, _ in week.achievements:
        scores[name] += ACHIEVEMENT_BP
    best = scores.most_common(1)
    return best[0][0] if best and best[0][1] > 0 else None


def top_lines(rows, describe):
    return [f"{MEDALS[place]} {row[0]} — {describe(row)}" for place, row in enumerate(rows[:TOP])]


def format_week(week):
    texts = kb.texts
    lines = [texts.week_title.format(first=f"{week.first_day:%d.%m}", last=f"{week.last_day:%d.%m}")]
    if week.messages:
        total = sum(count for _, count in week.messages)
        lines += ["", texts.week_talkers]
        lines += top_lines(week.messages, lambda row: f"{row[1]} {plural(row[1], *texts.message_forms)}")
        lines.append(texts.week_total.format(count=total, messages=plural(total, *texts.message_forms)))
    if week.correct_answers:
        lines += ["", texts.week_brains]
        lines += top_lines(week.correct_answers, lambda row: f"{row[1]} {plural(row[1], *texts.right_answer_forms)}")
    if week.loot:
        lines += ["", texts.week_farmers]
        lines += top_lines(
            week.loot,
            lambda row: (
                f"{row[1]} {kb.theme_data.points}" + (texts.week_top_loot.format(count=row[2]) if row[2] else "")
            ),
        )
    if week.fat_days:
        fatties = ", ".join(f"{name} {days} {times_word(days)}" for name, days in week.fat_days)
        lines += ["", texts.week_fatties.format(names=fatties)]
    if week.achievements:
        by_name = {}
        for name, code in week.achievements:
            by_name.setdefault(name, []).append(kb.theme_data.achievements[code][0])
        lines += ["", texts.week_medals]
        lines += [f"{name}: {', '.join(titles)}" for name, titles in by_name.items()]
    if week.parties:
        lines += ["", texts.week_parties.format(count=week.parties)]
    if week.quote:
        lines += ["", format_quote(week.quote, title=texts.week_quote)]
    # nobody wrote at all, e.g. the first week of counting: no point calling everyone silent
    if week.messages and week.silent:
        silent = ", ".join(mention(name, username) for name, username in week.silent)
        lines += ["", texts.week_silent.format(names=silent)]
    best = mvp(week)
    if best:
        lines += ["", texts.week_mvp.format(name=best)]
    if len(lines) == 1:
        lines += ["", texts.week_quiet]
    return "\n".join(lines)
