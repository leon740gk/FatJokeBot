from telegram_bots.engine.content import kb
from telegram_bots.engine.services.people import mention


def format_members(present, gone):
    """present and gone are lists of (telegram_id, name, username)."""
    lines = [kb.texts.members_present.format(count=len(present))]
    lines += [f"• {mention(name, username)} — {user_id}" for user_id, name, username in present]
    if gone:
        lines.append(kb.texts.members_gone.format(count=len(gone)))
        lines += [f"• {mention(name, username)} — {user_id}" for user_id, name, username in gone]
    lines.append(kb.texts.members_footer)
    return "\n".join(lines)
