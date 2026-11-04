"""Gaming news: RSS feeds from knowledge_base/<bot>/news_data.py, a short digest with links once a day."""

import asyncio
import html
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import aiohttp
from aiogram.utils.formatting import Text, TextLink

from telegram_bots.engine.content import kb

logger = logging.getLogger(__name__)
DIGEST_SIZE = 5
# older news are not news anymore; the digest is daily, a day and a half covers a late start
MAX_AGE = timedelta(hours=36)
FETCH_TIMEOUT = aiohttp.ClientTimeout(total=20)
# a feed is a few dozen kilobytes, anything much bigger is not what we asked for
MAX_FEED_BYTES = 2 * 1024 * 1024
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; telegram news bot)"}
ATOM = "{http://www.w3.org/2005/Atom}"


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    link: str
    published: datetime | None


def _date(text):
    if not text:
        return None
    try:
        value = parsedate_to_datetime(text.strip())
    except (TypeError, ValueError):
        try:
            value = datetime.fromisoformat(text.strip())
        except ValueError:
            return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _clean(text):
    # titles come with entities like &#8211;, sometimes encoded twice
    return " ".join(html.unescape(text or "").split())


def parse_feed(data, source):
    """NewsItems of an RSS 2.0 or Atom feed; an unreadable feed gives none."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        logger.warning("news feed %s is not valid XML: %s", source, error)
        return []
    items = []
    for item in root.iter("item"):
        items.append(
            NewsItem(
                source,
                _clean(item.findtext("title")),
                (item.findtext("link") or "").strip(),
                _date(item.findtext("pubDate")),
            )
        )
    for entry in root.iter(f"{ATOM}entry"):
        link = entry.find(f"{ATOM}link")
        published = entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated")
        items.append(
            NewsItem(
                source,
                _clean(entry.findtext(f"{ATOM}title")),
                link.get("href", "") if link is not None else "",
                _date(published),
            )
        )
    return [item for item in items if item.title and item.link.startswith(("https://", "http://"))]


def pick(items, sent_links, now, limit=DIGEST_SIZE):
    """Up to `limit` fresh items not sent before, the newest of each source in turn so every site gets a say."""
    by_source = {}
    seen = set(sent_links)
    for item in sorted(items, key=lambda item: item.published or now, reverse=True):
        if item.link in seen or (item.published and now - item.published > MAX_AGE):
            continue
        seen.add(item.link)
        by_source.setdefault(item.source, []).append(item)
    picked = []
    while len(picked) < limit and any(by_source.values()):
        for queue in by_source.values():
            if queue and len(picked) < limit:
                picked.append(queue.pop(0))
    return picked


def digest(items, today):
    parts = [kb.texts.news_title.format(date=f"{today:%d.%m}"), "\n"]
    for item in items:
        parts += ["\n▫️ ", TextLink(item.title, url=item.link), f" — {item.source}"]
    return Text(*parts)


async def _fetch(session, source, url):
    try:
        async with session.get(url, headers=HEADERS) as response:
            response.raise_for_status()
            # read() returns only what has arrived so far, a slow site would give half a feed
            data = bytearray()
            async for chunk in response.content.iter_chunked(64 * 1024):
                data += chunk
                if len(data) > MAX_FEED_BYTES:
                    logger.warning("news feed %s is over %s bytes, skipped", source, MAX_FEED_BYTES)
                    return []
    except (aiohttp.ClientError, TimeoutError) as error:
        logger.warning("can't fetch news feed %s: %s", source, error)
        return []
    return parse_feed(bytes(data), source)


async def fetch_all(feeds):
    """Items of every (source, url) feed; a broken feed is logged and skipped."""
    async with aiohttp.ClientSession(timeout=FETCH_TIMEOUT) as session:
        results = await asyncio.gather(*(_fetch(session, source, url) for source, url in feeds))
    return [item for items in results for item in items]
