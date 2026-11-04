def mention(name, username):
    """How the bot names a chat member in plain text: "Alex (@alex)", or just the name."""
    return f"{name} (@{username})" if username else name


def display_name(user):
    return user.first_name or user.username or str(user.id)
