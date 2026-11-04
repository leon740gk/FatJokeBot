import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from aiogram import methods
from aiogram.enums import MessageEntityType

from telegram_bots.engine import content
from telegram_bots.engine.db import news as news_db
from telegram_bots.engine.scheduler import create_scheduler
from telegram_bots.engine.services import news
from telegram_bots.tests.fake_telegram import CHAT, feed, sent_texts, text_update, user

NOW = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Site</title>
<item><title>NAVI &#8211; \xd1\x87\xd0\xb5\xd0\xbc\xd0\xbf\xd1\x96\xd0\xbe\xd0\xbd\xd0\xb8</title>
<link>https://site.ua/navi</link><pubDate>Wed, 04 Nov 2026 08:00:00 +0000</pubDate></item>
<item><title>Old news</title><link>https://site.ua/old</link><pubDate>Sun, 01 Nov 2026 08:00:00 +0000</pubDate></item>
<item><title>No link</title><pubDate>Wed, 04 Nov 2026 08:00:00 +0000</pubDate></item>
<item><title>Bad link</title><link>javascript:alert(1)</link></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Atom site</title>
<entry><title>Patch notes</title><link href="https://atom.ua/patch"/><updated>2026-11-04T07:00:00Z</updated></entry>
</feed>"""


def item(source, number, hours_ago):
    return news.NewsItem(
        source, f"{source} {number}", f"https://{source}.ua/{number}", NOW - timedelta(hours=hours_ago)
    )


def test_parse_rss_and_atom():
    rss = news.parse_feed(RSS, "Site")
    assert [(i.title, i.link) for i in rss] == [
        ("NAVI – чемпіони", "https://site.ua/navi"),
        ("Old news", "https://site.ua/old"),
    ]
    assert rss[0].published == datetime(2026, 11, 4, 8, 0, tzinfo=UTC)
    atom = news.parse_feed(ATOM, "Atom")
    assert [(i.title, i.link, i.published.hour) for i in atom] == [("Patch notes", "https://atom.ua/patch", 7)]
    assert news.parse_feed(b"<html>not a feed", "Broken") == []


def test_pick_takes_fresh_unsent_news_from_every_site():
    items = [item("a", n, n) for n in range(1, 6)] + [item("b", 1, 2), item("b", 2, 40)]
    picked = news.pick(items, sent_links={"https://a.ua/1"}, now=NOW, limit=4)
    # a/1 was sent before, b/2 is too old; the sites take turns, the newest first
    assert [i.title for i in picked] == ["a 2", "b 1", "a 3", "a 4"]
    # the same story in two feeds goes once
    assert len(news.pick([item("a", 1, 1), item("a", 1, 1)], set(), NOW)) == 1


def test_digest_links():
    text, entities = news.digest([item("a", 1, 1)], NOW.date()).render()
    assert text.startswith("🎮 Игровые новости, 04.11") and "a 1 — a" in text
    assert [(e.type, e.url) for e in entities] == [(MessageEntityType.TEXT_LINK, "https://a.ua/1")]


def test_sent_links_are_kept_per_chat(db):
    news_db.mark_sent(db, -1, ["https://a.ua/1", "https://a.ua/1"])
    assert news_db.sent_links(db, -1) == {"https://a.ua/1"} and news_db.sent_links(db, -2) == set()


@pytest.fixture
def servo_skull():
    content.activate("servo_skull")
    yield
    content.activate(content.DEFAULT_BOT)


def test_news_command(db, bot, dispatcher, servo_skull, monkeypatch):
    fetched = [item("PlayUA", 1, 1), item("ITC", 1, 2)]

    async def fake_fetch(feeds):
        assert feeds == content.kb.news_data.feeds
        return [news.NewsItem(i.source, i.title, i.link, datetime.now(UTC)) for i in fetched]

    monkeypatch.setattr(news, "fetch_all", fake_fetch)
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/news"))
    sent = bot.session.of_type(methods.SendMessage)[-1]
    assert sent.text.startswith("🎮 Ігрові новини") and sent.link_preview_options.is_disabled
    assert len(sent.entities) == 2
    # posted once: the same news don't come again, neither on /news nor in the morning
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/news"))
    assert sent_texts(bot)[-1].startswith("Свіжих новин поки немає")


def test_news_are_off_without_feeds(db, bot, dispatcher):
    feed(dispatcher, bot, **text_update(user(7, "Alex"), "/news"))
    assert sent_texts(bot)[-1] == "Новости у этого бота выключены 📰"
    # FatJoke has no feeds, so nothing is scheduled even with the flag on
    jobs = {job.func.__name__ for job in create_scheduler(bot, db, CHAT.id, news_enabled=True).get_jobs()}
    assert "daily_news" not in jobs


def test_daily_news_scheduled_for_servo_skull(db, bot, servo_skull):
    def jobs(**flags):
        return {job.func.__name__ for job in create_scheduler(bot, db, CHAT.id, **flags).get_jobs()}

    assert "daily_news" in jobs(news_enabled=True)
    assert "daily_news" not in jobs(news_enabled=False)


def test_a_dead_feed_is_skipped():
    async def run():
        return await news.fetch_all([("Dead", "http://127.0.0.1:9/feed")])

    assert asyncio.run(run()) == []


def test_a_slow_feed_is_read_to_the_end():
    """The server sends the feed in pieces with pauses, as a slow site does; the whole feed must be parsed."""
    from aiohttp import web

    async def slow_feed(request):
        response = web.StreamResponse(headers={"Content-Type": "application/rss+xml"})
        await response.prepare(request)
        for start in range(0, len(RSS), 100):
            await response.write(RSS[start : start + 100])
            await asyncio.sleep(0.01)
        await response.write_eof()
        return response

    async def run():
        app = web.Application()
        app.router.add_get("/feed", slow_feed)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = runner.addresses[0][1]
        try:
            return await news.fetch_all([("Slow", f"http://127.0.0.1:{port}/feed")])
        finally:
            await runner.cleanup()

    assert [i.link for i in asyncio.run(run())] == ["https://site.ua/navi", "https://site.ua/old"]
