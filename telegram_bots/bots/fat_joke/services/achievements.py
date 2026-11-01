import random
from dataclasses import dataclass

from telegram_bots.bots.fat_joke.db import achievements as achievements_db
from telegram_bots.bots.fat_joke.db import loot as loot_db
from telegram_bots.bots.fat_joke.services.fat_day import times_word
from telegram_bots.knowledge_base.fat_joke.mlbb_data import achievements as ACHIEVEMENTS
from telegram_bots.knowledge_base.fat_joke.mlbb_data import ranks, unlocked_phrases

# every achievement adds to Battle Points, so the rank grows not only from the loot
ACHIEVEMENT_BP = 20
NIGHT_HOURS = range(2, 5)


@dataclass(frozen=True)
class Stats:
    correct_answers: int
    best_streak: int
    loot: dict  # {kind: times taken}
    fat_days: int
    parties: int
    quotes: int


def best_streak(results):
    best = current = 0
    for is_correct in results:
        current = current + 1 if is_correct else 0
        best = max(best, current)
    return best


def collect(db, user_id):
    return Stats(
        correct_answers=achievements_db.correct_answers(db, user_id),
        best_streak=best_streak(achievements_db.answer_results(db, user_id)),
        loot=loot_db.taken_by_kind(db, user_id),
        fat_days=achievements_db.fat_days(db, user_id),
        parties=achievements_db.parties(db, user_id),
        quotes=achievements_db.quotes_authored(db, user_id),
    )


# code -> condition on (stats, Kyiv time now), the names are in mlbb_data.achievements
CONDITIONS = {
    "first_blood": lambda stats, now: stats.correct_answers >= 1,
    "double_kill": lambda stats, now: stats.best_streak >= 2,
    "triple_kill": lambda stats, now: stats.best_streak >= 3,
    "maniac": lambda stats, now: stats.best_streak >= 4,
    "savage": lambda stats, now: stats.best_streak >= 5,
    "legendary": lambda stats, now: stats.correct_answers >= 50,
    "buff_hunter": lambda stats, now: sum(stats.loot.values()) >= 10,
    "turtle_hunter": lambda stats, now: stats.loot.get("turtle", 0) >= 3,
    "lord_slayer": lambda stats, now: stats.loot.get("lord", 0) >= 1,
    "tank": lambda stats, now: stats.fat_days >= 3,
    "teammate": lambda stats, now: stats.parties >= 5,
    "mvp_quotes": lambda stats, now: stats.quotes >= 3,
    "night_farm": lambda stats, now: now.hour in NIGHT_HOURS,
}


def unlock_new(db, user_id, now):
    """Saves the achievements the user has just earned and returns their codes."""
    have = set(achievements_db.unlocked(db, user_id))
    stats = collect(db, user_id)
    earned = [code for code, condition in CONDITIONS.items() if code not in have and condition(stats, now)]
    return [code for code in earned if achievements_db.unlock(db, user_id, code)]


def battle_points(db, user_id):
    return loot_db.points(db, user_id) + ACHIEVEMENT_BP * len(achievements_db.unlocked(db, user_id))


def rank_for(points):
    return max((rank for rank in ranks if points >= rank[0]), key=lambda rank: rank[0])[1]


def next_rank(points):
    """(BP needed, rank) of the next rank, or None at the top."""
    return next(((low - points, name) for low, name in ranks if low > points), None)


def rank_up_line(who, old_points, new_points):
    new_rank = rank_for(new_points)
    if new_rank == rank_for(old_points):
        return None
    return f"⬆️ {who} поднимается до ранга {new_rank}!"


def announcement(who, codes, old_points, new_points, rng=random):
    lines = [
        rng.choice(unlocked_phrases).format(who=who, name=ACHIEVEMENTS[code][0])
        + f"\n   {ACHIEVEMENTS[code][1].capitalize()}, +{ACHIEVEMENT_BP} BP"
        for code in codes
    ]
    rank_up = rank_up_line(who, old_points, new_points)
    if rank_up:
        lines.append(rank_up)
    return "\n".join(lines)


def format_profile(name, iq_level, points, stats, unlocked_codes):
    lines = [f"👤 {name}", f"🏅 Ранг: {rank_for(points)}, {points} BP"]
    upcoming = next_rank(points)
    if upcoming:
        lines.append(f"   до {upcoming[1]}: ещё {upcoming[0]} BP")
    lords = stats.loot.get("lord", 0)
    lines += [
        "",
        f"🧠 IQ: {iq_level}",
        f"✅ Верных ответов: {stats.correct_answers}, лучшая серия: {stats.best_streak}",
        f"⚔️ Объектов из «Бам»: {sum(stats.loot.values())}" + (f", из них Лордов: {lords}" if lords else ""),
        f"🍩 Жиртрест дня: {stats.fat_days} {times_word(stats.fat_days)}",
        f"🎮 Пати: {stats.parties}",
        "",
        f"Достижения {len(unlocked_codes)}/{len(ACHIEVEMENTS)}:",
    ]
    lines += [f"{ACHIEVEMENTS[code][0]} — {ACHIEVEMENTS[code][1]}" for code in unlocked_codes]
    locked = [ACHIEVEMENTS[code] for code in ACHIEVEMENTS if code not in unlocked_codes]
    if locked:
        lines.append("\nЕщё закрыты:")
        lines += [f"🔒 {title.split(' ', 1)[1]} — {how}" for title, how in locked]
    return "\n".join(lines)


def format_ranks(rows):
    """rows of (name, BP)."""
    rows = sorted(rows, key=lambda row: -row[1])
    if not rows:
        return "Рейтинг пока пуст. Ловите объекты в «Бам» ⚔️"
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 Рейтинг чата по BP:\n"]
    for place, (name, points) in enumerate(rows):
        marker = medals[place] if place < len(medals) else f"{place + 1}."
        lines.append(f"{marker} {name} — {points} BP, {rank_for(points)}")
    lines.append("\nСвой профиль: /me")
    return "\n".join(lines)
