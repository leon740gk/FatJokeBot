from collections import Counter
from dataclasses import dataclass
from datetime import timedelta

from telegram_bots.bots.fat_joke.db import weekly as weekly_db
from telegram_bots.bots.fat_joke.services.achievements import ACHIEVEMENT_BP
from telegram_bots.bots.fat_joke.services.fat_day import times_word
from telegram_bots.bots.fat_joke.services.people import mention
from telegram_bots.bots.fat_joke.services.quotes import format_quote
from telegram_bots.knowledge_base.fat_joke.mlbb_data import achievements as ACHIEVEMENTS

MEDALS = ["🥇", "🥈", "🥉"]
TOP = 3


@dataclass(frozen=True)
class Week:
    first_day: object  # date
    last_day: object
    messages: list  # (name, count)
    silent: list  # (name, username)
    correct_answers: list  # (name, count)
    loot: list  # (name, BP, Lords)
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


def plural(count, one, few, many):
    if 11 <= count % 100 <= 14:
        return many
    if count % 10 == 1:
        return one
    if count % 10 in (2, 3, 4):
        return few
    return many


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
    lines = [f"📅 Итоги недели {week.first_day:%d.%m} – {week.last_day:%d.%m}"]
    if week.messages:
        total = sum(count for _, count in week.messages)
        lines += ["", "💬 Болтуны недели:"]
        lines += top_lines(
            week.messages, lambda row: f"{row[1]} {plural(row[1], 'сообщение', 'сообщения', 'сообщений')}"
        )
        lines.append(f"Всего в чате: {total} {plural(total, 'сообщение', 'сообщения', 'сообщений')}")
    if week.correct_answers:
        lines += ["", "🧠 Мозги недели:"]
        lines += top_lines(
            week.correct_answers,
            lambda row: f"{row[1]} {plural(row[1], 'верный ответ', 'верных ответа', 'верных ответов')}",
        )
    if week.loot:
        lines += ["", "⚔️ Фармеры недели:"]
        lines += top_lines(week.loot, lambda row: f"{row[1]} BP" + (f", Лордов: {row[2]}" if row[2] else ""))
    if week.fat_days:
        fatties = ", ".join(f"{name} {days} {times_word(days)}" for name, days in week.fat_days)
        lines += ["", f"🍩 Жиртресты недели: {fatties}"]
    if week.achievements:
        by_name = {}
        for name, code in week.achievements:
            by_name.setdefault(name, []).append(ACHIEVEMENTS[code][0])
        lines += ["", "🏆 Новые медали:"]
        lines += [f"{name}: {', '.join(titles)}" for name, titles in by_name.items()]
    if week.parties:
        lines += ["", f"🎮 Собрано пати: {week.parties}"]
    if week.quote:
        lines += ["", format_quote(week.quote, title="📜 Цитата недели")]
    # nobody wrote at all, e.g. the first week of counting: no point calling everyone silent
    if week.messages and week.silent:
        silent = ", ".join(mention(name, username) for name, username in week.silent)
        lines += ["", f"🦗 Молчуны недели: {silent}. Мы скучаем, напишите хоть что-нибудь!"]
    best = mvp(week)
    if best:
        lines += ["", f"👑 MVP недели: {best}!"]
    if len(lines) == 1:
        lines += ["", "Тихая неделя... Даже жиртреста никто не вычислил. Исправляйтесь: /fat /quiz /party 🙃"]
    return "\n".join(lines)
