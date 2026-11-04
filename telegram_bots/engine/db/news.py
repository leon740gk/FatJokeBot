# links stay longer than news stay fresh (services/news.MAX_AGE), so nothing is posted twice
KEEP_DAYS = 30


def sent_links(db, chat_id):
    return {row[0] for row in db.fetch_all("SELECT link FROM NewsSent WHERE chat_id = ?", (chat_id,))}


def mark_sent(db, chat_id, links):
    for link in links:
        db.execute("INSERT OR IGNORE INTO NewsSent (chat_id, link) VALUES (?, ?)", (chat_id, link))
    db.execute("DELETE FROM NewsSent WHERE sent_at < datetime('now', ?)", (f"-{KEEP_DAYS} days",))
