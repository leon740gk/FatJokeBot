from telegram_bots.engine.content import kb

PRIZES = {1: "🥇", 2: "🥈", 3: "🥉"}


def level_for(iq_level):
    """[title, emoji] of the highest level the IQ reaches, from texts.iq_levels."""
    levels = kb.texts.iq_levels
    low_limit = max((limit for limit in levels if iq_level >= limit), default=0)
    return levels[low_limit]


def format_iq_table(rows):
    lines = []
    for place, (name, iq_level) in enumerate(sorted(rows, key=lambda row: -row[1]), start=1):
        title, emoji = level_for(iq_level)
        lines.append(
            kb.texts.iq_row.format(prize=PRIZES.get(place, ""), name=name, iq=iq_level, title=title, emoji=emoji)
        )
    return "".join(lines)


def change_message(iq_old, user_name, increase):
    iq_new = iq_old + 1 if increase else iq_old - 1
    template = kb.texts.iq_up if increase else kb.texts.iq_down
    return iq_new, template.format(old=iq_old, new=iq_new, name=user_name)


def anti_cheat_message(user_name):
    return kb.texts.anti_cheat.format(name=user_name)
