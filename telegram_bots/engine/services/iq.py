import json
import logging

from telegram_bots.engine.content import kb
from telegram_bots.engine.db import settings as settings_db
from telegram_bots.engine.db import users as users_db

logger = logging.getLogger(__name__)
SEASON_KEY = "iq_season"

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


def start_new_season(db):
    """Resets everyone's IQ when theme_data.iq_season has been raised; the old numbers stay in Settings."""
    season = int(settings_db.get(db, SEASON_KEY, 1))
    if kb.theme_data.iq_season <= season:
        return False
    settings_db.set_value(db, f"iq_of_season_{season}", json.dumps(users_db.get_iq_by_id(db)))
    users_db.reset_iq(db)
    settings_db.set_value(db, SEASON_KEY, str(kb.theme_data.iq_season))
    logger.info("IQ season %s has started", kb.theme_data.iq_season)
    return True
