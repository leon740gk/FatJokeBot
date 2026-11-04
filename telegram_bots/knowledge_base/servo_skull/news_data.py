# The gaming news at 10:00 Kyiv time, see engine/services/news.py.
# Ukrainian sites, both checked on 2026-11-04. A site that is down is skipped, the other still posts.

# (section, site name, RSS url)
feeds = [
    ("games", "PlayUA", "https://playua.net/feed/"),
    ("games", "ITC.ua", "https://itc.ua/ua/igri/feed/"),
]
# one section, so no heading over the list
sections = {"games": ""}
per_section = 5
skip_words = []
