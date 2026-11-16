import random
from dataclasses import dataclass
from datetime import timedelta

from telegram_bots.engine.content import active, kb

# the day is cut into windows of this many hours, each spawns loot with LOOT_CHANCE at a random moment inside,
# so it comes at night as often as in the daytime and never at the same time: 4 windows * 0.75 = 3 a day
WINDOW_HOURS = 6
LOOT_CHANCE = 0.75
# nobody pressed in this long, the objective is gone
LOOT_MINUTES = 120
CALLBACK = "loot"


@dataclass(frozen=True)
class LootKind:
    code: str
    weight: int
    points: int
    spawn_line: str
    taken_line: str


_kinds = {}


def kinds():
    """{code: LootKind} of the running bot's theme."""
    if active() not in _kinds:
        _kinds[active()] = {kind[0]: LootKind(*kind) for kind in kb.theme_data.loot_kinds}
    return _kinds[active()]


def roll(rng=random):
    """The objective that spawns, by the weights of the kinds."""
    kinds_list = list(kinds().values())
    return rng.choices(kinds_list, weights=[kind.weight for kind in kinds_list])[0]


def spawn_time(now, rng=random):
    """A random moment from now to the end of its window, or None if this window has no loot."""
    if rng.random() >= LOOT_CHANCE:
        return None
    window_start = now.replace(hour=now.hour - now.hour % WINDOW_HOURS, minute=0, second=0, microsecond=0)
    left = (window_start + timedelta(hours=WINDOW_HOURS) - now).total_seconds()
    return now + timedelta(seconds=rng.uniform(0, left))


def spawn_text(kind):
    return f"{kind.spawn_line}\n" + kb.texts.loot_first_takes.format(points=kind.points)


def _with_bam(bam_text, lines):
    return "\n".join([bam_text, "", *lines] if bam_text else lines)


def taken_text(bam_text, kind, who, extra_lines=()):
    taken_line = f"{kind.taken_line.format(who=who)}: +{kind.points} {kb.theme_data.points}"
    return _with_bam(bam_text, [taken_line, *extra_lines])


def gone_text(bam_text):
    return _with_bam(bam_text, [kb.theme_data.gone_line])


def bam_part(text):
    """The "Бам" over the loot lines of a message from before the loot had its own; empty for a loot message."""
    head, empty_line, _ = (text or "").partition("\n\n")
    return head if empty_line else ""
