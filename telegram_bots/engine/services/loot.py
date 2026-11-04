import random
from dataclasses import dataclass

from telegram_bots.engine.content import active, kb

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


_kinds = {}


def kinds():
    """{code: LootKind} of the running bot's theme."""
    if active() not in _kinds:
        _kinds[active()] = {kind[0]: LootKind(*kind) for kind in kb.theme_data.loot_kinds}
    return _kinds[active()]


def roll(rng=random):
    """The objective that spawns under this "Бам", or None."""
    if rng.random() >= LOOT_CHANCE:
        return None
    kinds_list = list(kinds().values())
    return rng.choices(kinds_list, weights=[kind.weight for kind in kinds_list])[0]


def spawn_text(bam_text, kind):
    return f"{bam_text}\n\n{kind.spawn_line}\n" + kb.texts.loot_first_takes.format(points=kind.points)


def taken_text(bam_text, kind, who, extra_lines=()):
    return "\n".join(
        [bam_text, "", f"{kind.taken_line.format(who=who)}: +{kind.points} {kb.theme_data.points}", *extra_lines]
    )


def bam_part(text):
    """The "Бам" itself without the loot lines, they start after the first empty line."""
    return (text or "").split("\n\n")[0]
