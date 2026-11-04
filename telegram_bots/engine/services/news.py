"""News: RSS feeds from knowledge_base/<bot>/news_data.py, a short digest with links once a day.

news_data.py of a bot has:
  feeds = [(section, site name, RSS url)]  # empty turns the news off
  sections = {section: header}             # the digest order; an empty header shows no heading
  per_section = 3                          # news in each section
  skip_words = ["рубл"]                    # a title with a word starting like this is skipped
"""

import asyncio
import html
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import aiohttp
from aiogram.utils.formatting import Text, TextLink

from telegram_bots.engine.content import kb

logger = logging.getLogger(__name__)
# older news are not news anymore; the digest is daily, a day and a half covers a late start
MAX_AGE = timedelta(hours=36)
FETCH_TIMEOUT = aiohttp.ClientTimeout(total=20)
# a feed is a few dozen kilobytes, anything much bigger is not what we asked for
MAX_FEED_BYTES = 2 * 1024 * 1024
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; telegram news bot)"}
ATOM = "{http://www.w3.org/2005/Atom}"


@dataclass(frozen=True)
class NewsItem:
    section: str
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


def parse_feed(data, source, section=""):
    """NewsItems of an RSS 2.0 or Atom feed; an unreadable feed gives none."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        logger.warning("news feed %s is not valid XML: %s", source, error)
        return []
    found = []
    for item in root.iter("item"):
        found.append((item.findtext("title"), item.findtext("link"), item.findtext("pubDate")))
    for entry in root.iter(f"{ATOM}entry"):
        link = entry.find(f"{ATOM}link")
        published = entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated")
        found.append((entry.findtext(f"{ATOM}title"), link.get("href") if link is not None else None, published))
    items = [
        NewsItem(section, source, _clean(title), (link or "").strip(), _date(published))
        for title, link, published in found
    ]
    return [item for item in items if item.title and item.link.startswith(("https://", "http://"))]


def skipped(title, skip_words):
    """True if a word of the title starts with one of skip_words, case-insensitive."""
    return any(re.search(rf"(?<!\w){re.escape(word)}", title.lower()) for word in skip_words)


def pick(items, sent_links, now, per_section, skip_words=()):
    """Up to per_section fresh items of each section, not sent before; the sites of a section take turns.

    Returns {section: [NewsItem]}; a story in two feeds goes once.
    """
    seen = set(sent_links)
    queues = {}  # section -> source -> items, the newest first
    for item in sorted(items, key=lambda item: item.published or now, reverse=True):
        if item.link in seen or (item.published and now - item.published > MAX_AGE):
            continue
        if skipped(item.title, skip_words):
            continue
        seen.add(item.link)
        queues.setdefault(item.section, {}).setdefault(item.source, []).append(item)
    picked = {}
    for section, by_source in queues.items():
        chosen = []
        while len(chosen) < per_section and any(by_source.values()):
            for queue in by_source.values():
                if queue and len(chosen) < per_section:
                    chosen.append(queue.pop(0))
        picked[section] = chosen
    return picked


def digest(picked, sections, today):
    """picked is {section: [NewsItem]} from pick(), sections the {section: header} of the bot."""
    parts = [kb.texts.news_title.format(date=f"{today:%d.%m}"), "\n"]
    for section, header in sections.items():
        if not picked.get(section):
            continue
        if header:
            parts += ["\n", header]
        for item in picked[section]:
            parts += ["\n▫️ ", TextLink(item.title, url=item.link), f" — {item.source}"]
        if header:
            parts.append("\n")
    return Text(*parts)


async def _fetch(session, section, source, url):
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
    return parse_feed(bytes(data), source, section)


async def fetch_all(feeds):
    """Items of every (section, source, url) feed; a broken feed is logged and skipped."""
    async with aiohttp.ClientSession(timeout=FETCH_TIMEOUT) as session:
        results = await asyncio.gather(*(_fetch(session, *feed) for feed in feeds))
    return [item for items in results for item in items]
