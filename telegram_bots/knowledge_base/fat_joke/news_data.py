# The news at 10:00 Kyiv time: games, IT and AI, in Russian; see engine/services/news.py.
# Feeds checked on 2026-11-04. A site that is down is skipped, the others still post.

# (section, site name, RSS url)
feeds = [
    ("games", "StopGame", "https://stopgame.ru/rss/rss_news.xml"),
    ("games", "Игромания", "https://www.igromania.ru/rss/news.rss"),
    ("it", "Хабр", "https://habr.com/ru/rss/news/?fl=ru"),
    # a Ukrainian site, its main feed is in Russian
    ("it", "ITC.ua", "https://itc.ua/feed/"),
    ("ai", "Хабр", "https://habr.com/ru/rss/flows/ai_and_ml/news/?fl=ru"),
]
sections = {
    "games": "🎮 Игры",
    "it": "💻 IT",
    "ai": "🤖 AI",
}
per_section = 3
# most Russian-language sites are Russian, their news about Russia itself are no use in our chat:
# a title with a word starting like one of these is skipped
skip_words = [
    "росси",
    "рф",
    "россиян",
    "москв",
    "кремл",
    "путин",
    "госдум",
    "роскомнадзор",
    "ркн",
    "минцифр",
    "рубл",
    "импортозамещ",
    "отечествен",
    "госуслуг",
    "яндекс",
    "сбер",
    "вконтакт",
    "ростелеком",
    "мтс",
    "rutube",
]
