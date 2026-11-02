"""Bets on duels: `side` is the duelist bet on, `payout` stays NULL until the duel is settled."""


def get(db, duel_id, user_id):
    """(side, amount) of the user's bet on the duel, or None."""
    return db.fetch_one("SELECT side, amount FROM DuelBets WHERE duel_id = ? AND telegram_id = ?", (duel_id, user_id))


def add(db, duel_id, user_id, side, amount):
    db.execute(
        """
        INSERT INTO DuelBets (duel_id, telegram_id, side, amount) VALUES (?, ?, ?, ?)
        ON CONFLICT (duel_id, telegram_id) DO UPDATE SET amount = amount + excluded.amount
        """,
        (duel_id, user_id, side, amount),
    )


def for_duel(db, duel_id):
    """(telegram_id, side, amount) of every bet on the duel."""
    return db.fetch_all("SELECT telegram_id, side, amount FROM DuelBets WHERE duel_id = ? ORDER BY rowid", (duel_id,))


def settle(db, duel_id, payouts):
    """payouts: {telegram_id: BP returned to the user, the stake included}; only unsettled bets change."""
    for user_id, payout in payouts.items():
        db.execute(
            "UPDATE DuelBets SET payout = ? WHERE duel_id = ? AND telegram_id = ? AND payout IS NULL",
            (payout, duel_id, user_id),
        )


def balance_change(db, user_id):
    """Payouts minus stakes; a stake leaves the balance as soon as it is made."""
    return db.fetch_one(
        "SELECT COALESCE(SUM(COALESCE(payout, 0) - amount), 0) FROM DuelBets WHERE telegram_id = ?", (user_id,)
    )[0]
