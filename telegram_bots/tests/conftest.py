from types import SimpleNamespace

import pytest

from telegram_bots.bots.fat_joke.db.connection import Database
from telegram_bots.bots.fat_joke.db.schema import init_schema


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
