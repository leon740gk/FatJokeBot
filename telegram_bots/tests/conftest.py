from types import SimpleNamespace

import pytest
from aiogram import Bot

from telegram_bots.engine import main
from telegram_bots.engine.db.connection import Database
from telegram_bots.engine.db.schema import init_schema
from telegram_bots.engine.services import achievements
from telegram_bots.tests.fake_telegram import FakeSession


@pytest.fixture
def db():
    database = Database(":memory:")
    init_schema(database)
    yield database
    database.close()


def make_user(user_id, first_name="Test", username=None):
    return SimpleNamespace(id=user_id, first_name=first_name, username=username, is_bot=False)


class FakeRandom:
    """random.Random stand-in with a fixed random() value and choice() picking the first item."""

    def __init__(self, value=0.99):
        self.value = value

    def random(self):
        return self.value

    def choice(self, items):
        return list(items)[0]


@pytest.fixture
def bot(monkeypatch):
    """A bot that talks to FakeSession instead of Telegram."""
    # a random philosopher quote on any text message would add an unexpected reply now and then
    monkeypatch.setattr("telegram_bots.engine.services.reactions.PHILOSOPHY_CHANCE", 0)
    # tests run at night too, the night achievement would add a message
    monkeypatch.setattr(achievements, "NIGHT_HOURS", range(0))
    return Bot("42:TEST", session=FakeSession())


@pytest.fixture
def dispatcher(db):
    yield main.build_dispatcher(db)
    # module level routers can belong to one dispatcher only, detach them for the next test
    for router in main.ROUTERS:
        router._parent_router = None
