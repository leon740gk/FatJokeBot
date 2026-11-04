import random
from dataclasses import dataclass

from telegram_bots.engine.content import kb
from telegram_bots.engine.db import achievements as achievements_db
from telegram_bots.engine.db import bets as bets_db
from telegram_bots.engine.db import duels as duels_db
from telegram_bots.engine.db import loot as loot_db
from telegram_bots.engine.services.fat_day import times_word

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
    duels_won: int = 0


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
        duels_won=duels_db.wins(db, user_id),
    )


# code -> condition on (stats, Kyiv time now), the names are in theme_data.achievements of the bot
CONDITIONS = {
    "first_blood": lambda stats, now: stats.correct_answers >= 1,
    "double_kill": lambda stats, now: stats.best_streak >= 2,
    "triple_kill": lambda stats, now: stats.best_streak >= 3,
    "maniac": lambda stats, now: stats.best_streak >= 4,
    "savage": lambda stats, now: stats.best_streak >= 5,
    "legendary": lambda stats, now: stats.correct_answers >= 50,
    "buff_hunter": lambda stats, now: sum(stats.loot.values()) >= 10,
    # the second rarest and the rarest loot of the bot's theme, a Turtle and the Lord in MLBB
    "turtle_hunter": lambda stats, now: stats.loot.get(kb.theme_data.rare_loot, 0) >= 3,
    "lord_slayer": lambda stats, now: stats.loot.get(kb.theme_data.top_loot, 0) >= 1,
    "tank": lambda stats, now: stats.fat_days >= 3,
    "teammate": lambda stats, now: stats.parties >= 5,
    "mvp_quotes": lambda stats, now: stats.quotes >= 3,
    "duelist": lambda stats, now: stats.duels_won >= 3,
    "night_farm": lambda stats, now: now.hour in NIGHT_HOURS,
}


def unlock_new(db, user_id, now):
    """Saves the achievements the user has just earned and returns their codes."""
    have = set(achievements_db.unlocked(db, user_id))
    stats = collect(db, user_id)
    earned = [code for code, condition in CONDITIONS.items() if code not in have and condition(stats, now)]
    return [code for code in earned if achievements_db.unlock(db, user_id, code)]


def battle_points(db, user_id):
    return (
        loot_db.points(db, user_id)
        + duels_db.points(db, user_id)
        + bets_db.balance_change(db, user_id)
        + ACHIEVEMENT_BP * len(achievements_db.unlocked(db, user_id))
    )


def rank_for(points):
    return max((rank for rank in kb.theme_data.ranks if points >= rank[0]), key=lambda rank: rank[0])[1]


def next_rank(points):
    """(BP needed, rank) of the next rank, or None at the top."""
    return next(((low - points, name) for low, name in kb.theme_data.ranks if low > points), None)


def rank_up_line(who, old_points, new_points):
    new_rank = rank_for(new_points)
    if new_rank == rank_for(old_points):
        return None
    return kb.texts.rank_up.format(who=who, rank=new_rank)


def announcement(who, codes, old_points, new_points, rng=random):
    achievements = kb.theme_data.achievements
    lines = [
        rng.choice(kb.theme_data.unlocked_phrases).format(who=who, name=achievements[code][0])
        + f"\n   {achievements[code][1].capitalize()}, +{ACHIEVEMENT_BP} BP"
        for code in codes
    ]
    rank_up = rank_up_line(who, old_points, new_points)
    if rank_up:
        lines.append(rank_up)
    return "\n".join(lines)


def format_profile(name, iq_level, points, stats, unlocked_codes):
    texts, achievements = kb.texts, kb.theme_data.achievements
    lines = [f"👤 {name}", texts.profile_rank.format(rank=rank_for(points), points=points)]
    upcoming = next_rank(points)
    if upcoming:
        lines.append(texts.profile_next_rank.format(rank=upcoming[1], points=upcoming[0]))
    top = stats.loot.get(kb.theme_data.top_loot, 0)
    lines += [
        "",
        f"🧠 IQ: {iq_level}",
        texts.profile_answers.format(correct=stats.correct_answers, streak=stats.best_streak),
        texts.profile_loot.format(count=sum(stats.loot.values()))
        + (texts.profile_top_loot.format(count=top) if top else ""),
        texts.profile_fat_days.format(count=stats.fat_days, times=times_word(stats.fat_days)),
        texts.profile_parties.format(count=stats.parties),
        texts.profile_duels.format(count=stats.duels_won),
        "",
        texts.profile_achievements.format(have=len(unlocked_codes), total=len(achievements)),
    ]
    lines += [f"{achievements[code][0]} — {achievements[code][1]}" for code in unlocked_codes]
    locked = [achievements[code] for code in achievements if code not in unlocked_codes]
    if locked:
        lines.append(texts.profile_locked)
        lines += [f"🔒 {title.split(' ', 1)[1]} — {how}" for title, how in locked]
    return "\n".join(lines)


def format_ranks(rows):
    """rows of (name, BP)."""
    rows = sorted(rows, key=lambda row: -row[1])
    if not rows:
        return kb.texts.ranks_empty
    medals = ["🥇", "🥈", "🥉"]
    lines = [kb.texts.ranks_title]
    for place, (name, points) in enumerate(rows):
        marker = medals[place] if place < len(medals) else f"{place + 1}."
        lines.append(f"{marker} {name} — {points} BP, {rank_for(points)}")
    lines.append(kb.texts.ranks_footer)
    return "\n".join(lines)
