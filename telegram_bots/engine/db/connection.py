import sqlite3


class Database:
    """Thin wrapper over one sqlite3 connection.

    The bot runs in a single asyncio thread, so one connection is enough and
    queries never race each other.
    """

    def __init__(self, path):
        self.connection = sqlite3.connect(path)

    def fetch_all(self, query, params=()):
        return self.connection.execute(query, params).fetchall()

    def fetch_one(self, query, params=()):
        return self.connection.execute(query, params).fetchone()

    def execute(self, query, params=()):
        """Runs a write query, commits and returns the number of changed rows."""
        cursor = self.connection.execute(query, params)
        self.connection.commit()
        return cursor.rowcount

    def close(self):
        self.connection.close()
