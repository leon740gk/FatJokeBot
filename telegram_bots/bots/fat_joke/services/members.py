from telegram_bots.bots.fat_joke.services.people import mention


def format_members(present, gone):
    """present and gone are lists of (telegram_id, name, username)."""
    lines = [f"👥 В чате ({len(present)}):"]
    lines += [f"• {mention(name, username)} — {user_id}" for user_id, name, username in present]
    if gone:
        lines.append(f"\n🚪 Ушли ({len(gone)}):")
        lines += [f"• {mention(name, username)} — {user_id}" for user_id, name, username in gone]
    lines.append("\nКто ни разу не писал при боте, появится здесь после первого сообщения.")
    return "\n".join(lines)
