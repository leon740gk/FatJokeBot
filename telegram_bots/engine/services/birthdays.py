"""Birthdays: Users.DOB keeps "DD.MM.YYYY", or "DD.MM" when the year is unknown."""

import random
import re
from dataclasses import dataclass
from datetime import date

from aiogram.types import User
from aiogram.utils.formatting import Text, TextMention

from telegram_bots.engine.content import kb
from telegram_bots.engine.services.words import plural

FIRST_YEAR = 1900
# a leap day birthday is celebrated on February 28 in other years
LEAP_DAY = (2, 29)


@dataclass(frozen=True)
class Birthday:
    day: int
    month: int
    year: int | None = None

    def stored(self):
        """The value for Users.DOB."""
        return f"{self.day:02d}.{self.month:02d}" + (f".{self.year}" if self.year else "")

    def date_in(self, year):
        """The day it is celebrated in `year`."""
        if (self.month, self.day) == LEAP_DAY and not _is_leap(year):
            return date(year, 2, 28)
        return date(year, self.month, self.day)

    def age_on(self, day):
        return day.year - self.year if self.year else None


def _is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def parse(text, today=None):
    """Birthday from "03.05", "3/5", "03.05.1990" or "03-05-1990"; None if it isn't a real date."""
    match = re.fullmatch(r"\s*(\d{1,2})[./-](\d{1,2})(?:[./-](\d{4}))?\s*", text or "")
    if not match:
        return None
    day, month = int(match.group(1)), int(match.group(2))
    year = int(match.group(3)) if match.group(3) else None
    today = today or date.today()
    if year is not None and not FIRST_YEAR <= year <= today.year:
        return None
    try:
        # 2000 is a leap year, so 29.02 without a year is fine
        birthday = date(year or 2000, month, day)
    except ValueError:
        return None
    if year and birthday > today:
        return None
    return Birthday(day, month, year)


def next_date(birthday, today):
    this_year = birthday.date_in(today.year)
    return this_year if this_year >= today else birthday.date_in(today.year + 1)


def todays(rows, today):
    """(telegram_id, name, username, Birthday) of everyone celebrating today; rows have DOB as stored text."""
    found = []
    for user_id, name, username, stored in rows:
        birthday = parse(stored, today)
        if birthday and birthday.date_in(today.year) == today:
            found.append((user_id, name, username, birthday))
    return found


def upcoming(rows, today):
    """(name, Birthday, next date) of everyone with a known birthday, the nearest first."""
    known = [(name, parse(stored, today)) for _, name, _, stored in rows]
    found = [(name, birthday, next_date(birthday, today)) for name, birthday in known if birthday]
    return sorted(found, key=lambda item: (item[2], item[0]))


def format_upcoming(rows, today):
    found = upcoming(rows, today)
    if not found:
        return kb.texts.birthdays_empty
    lines = [kb.texts.birthdays_title]
    for name, birthday, when in found:
        days = (when - today).days
        if days == 0:
            soon = kb.texts.birthdays_today
        else:
            soon = kb.texts.birthdays_in.format(days=days, days_word=plural(days, *kb.texts.day_forms))
        lines.append(f"🎂 {name} — {birthday.date_in(when.year):%d.%m} ({soon})")
    lines.append(kb.texts.birthdays_footer)
    return "\n".join(lines)


def greeting(people, today, rng=random):
    """The morning greeting with a real mention of everyone celebrating, so they get a notification."""
    parts = [rng.choice(kb.texts.birthday_openers), "\n\n"]
    for index, (user_id, name, _, birthday) in enumerate(people):
        if index:
            parts.append("\n")
        parts.append("🎂 ")
        parts.append(TextMention(name, user=User(id=user_id, is_bot=False, first_name=name)))
        age = birthday.age_on(today)
        if age:
            parts.append(kb.texts.birthday_age.format(age=age, years=plural(age, *kb.texts.year_forms)))
    parts += ["\n\n", rng.choice(kb.texts.birthday_wishes)]
    return Text(*parts)
