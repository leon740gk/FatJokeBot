import random
from dataclasses import dataclass

from telegram_bots.knowledge_base.fat_joke.mlbb_data import loot_kinds

# share of daytime "Бам" with something to take, quiet hours never have loot
LOOT_CHANCE = 0.6
# nobody pressed in this long, the objective is gone; the next "Бам" comes in 3 hours
LOOT_MINUTES = 120
CALLBACK = "loot"


@dataclass(frozen=True)
class LootKind:
    code: str
    weight: int
    points: int
    spawn_line: str
    taken_line: str


KINDS = {kind[0]: LootKind(*kind) for kind in loot_kinds}


def roll(rng=random):
    """The objective that spawns under this "Бам", or None."""
    if rng.random() >= LOOT_CHANCE:
        return None
    kinds = list(KINDS.values())
    return rng.choices(kinds, weights=[kind.weight for kind in kinds])[0]


def spawn_text(bam_text, kind):
    return f"{bam_text}\n\n{kind.spawn_line}\nКто первый нажмёт, тот и заберёт: +{kind.points} BP"


def taken_text(bam_text, kind, who, extra_lines=()):
    return "\n".join([bam_text, "", f"{kind.taken_line.format(who=who)}: +{kind.points} BP", *extra_lines])


def bam_part(text):
    """The "Бам" itself without the loot lines, they start after the first empty line."""
    return (text or "").split("\n\n")[0]
