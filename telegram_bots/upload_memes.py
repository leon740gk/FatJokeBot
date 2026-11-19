"""Uploads the pictures of the meme quiz to Telegram and writes their file ids into the bot's quiz/memes.json.

A file id works only for the bot that uploaded the picture, so each bot needs its own run:
    .venv/bin/python -m telegram_bots.upload_memes fat_joke memes/ <your Telegram id>
    .venv/bin/python -m telegram_bots.upload_memes servo_skull memes/ <your Telegram id>

The pictures are <meme code>.jpg or .png, e.g. memes/doge.jpg; they arrive in the private chat with the bot
(press Start there first; /chat_id in that chat tells your id). Memes that already have a photo are skipped,
so a run that broke halfway just goes on. The pictures themselves stay out of git, the repository is public.
"""

import asyncio
import json
import sys
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

from telegram_bots.config import load_settings, require_token
from telegram_bots.engine.content import KNOWLEDGE_BASE

# Telegram lets a bot send about one message a second to one chat
PAUSE_SECONDS = 1.1


def picture_of(images, code):
    return next((path for path in sorted(images.glob(f"{code}.*")) if path.suffix in (".jpg", ".jpeg", ".png")), None)


async def upload(bot_name, images, chat_id):
    catalog_path = KNOWLEDGE_BASE / bot_name / "quiz" / "memes.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    settings = load_settings(bot_name)
    require_token(settings)
    bot = Bot(settings.token)
    uploaded = 0
    try:
        for meme in catalog["memes"]:
            if meme.get("photo"):
                continue
            picture = picture_of(images, meme["code"])
            if not picture:
                print(f"no picture for {meme['code']}")
                continue
            sent = await bot.send_photo(chat_id, FSInputFile(picture), caption=f"{meme['number']}. {meme['name']}")
            meme["photo"] = sent.photo[-1].file_id
            uploaded += 1
            # written after every picture: a broken run keeps what it has uploaded
            catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            await asyncio.sleep(PAUSE_SECONDS)
    finally:
        await bot.session.close()
    left = sum(not meme.get("photo") for meme in catalog["memes"])
    print(f"uploaded {uploaded}, without a photo: {left}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    asyncio.run(upload(sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])))
