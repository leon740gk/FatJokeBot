def get(db, key, default=None):
    row = db.fetch_one("SELECT value FROM Settings WHERE key = ?", (key,))
    return row[0] if row else default


def set_value(db, key, value):
    db.execute(
        "INSERT INTO Settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = ?", (key, value, value)
    )
