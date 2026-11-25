# accounts Telegram itself writes from: channel posts in the linked group, anonymous admins and channels;
# not all of them have is_bot set
SERVICE_IDS = (
    777000,  # Telegram
    1087968824,  # GroupAnonymousBot, shows up as "Group"
    136817688,  # Channel_Bot, shows up as "Channel"
)


def is_person(user):
    """Whether the Telegram user can take part in the chat's games, i.e. is no bot and no service account."""
    return not user.is_bot and user.id not in SERVICE_IDS


def mention(name, username):
    """How the bot names a chat member in plain text: "Alex (@alex)", or just the name."""
    return f"{name} (@{username})" if username else name


def display_name(user):
    return user.first_name or user.username or str(user.id)
