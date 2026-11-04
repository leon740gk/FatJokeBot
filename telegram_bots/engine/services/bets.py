from telegram_bots.engine.content import kb
from telegram_bots.engine.db import bets as bets_db

MAX_BET = 50
BUTTON_STAKE = 10


def callback(duel_id, side):
    return f"bet {duel_id} {side}"


def parse_callback(data):
    """(duel id, duelist bet on) or None; "bet <duel id> <side>"."""
    parts = (data or "").split(" ")
    if len(parts) == 3 and parts[0] == "bet" and parts[1].isdigit() and parts[2].isdigit():
        return int(parts[1]), int(parts[2])
    return None


def check(db, current, user_id, side, amount, balance):
    """Why the bet can't be made, or None if it can."""
    if current.status != "pending":
        return kb.texts.bet_too_late
    if user_id in (current.challenger, current.opponent):
        return kb.texts.bet_by_duelist
    if side not in (current.challenger, current.opponent):
        return kb.texts.bet_on_outsider
    if amount < 1:
        return kb.texts.bet_too_small
    placed = bets_db.get(db, current.id, user_id)
    if placed and placed[0] != side:
        return kb.texts.bet_other_side
    if (placed[1] if placed else 0) + amount > MAX_BET:
        return kb.texts.bet_too_big.format(max=MAX_BET)
    if amount > balance:
        return kb.texts.bet_no_money.format(balance=balance)
    return None


def payouts(bets, winner):
    """{telegram_id: BP back}: winners get their stake and share the losers' bank by their stakes.

    No winner (a draw, a cancelled duel) or nobody bet on the winner: everyone gets the stake back.
    """
    on_winner = sum(amount for _, side, amount in bets if side == winner)
    if winner is None or not on_winner:
        return {user_id: amount for user_id, _, amount in bets}
    lost = sum(amount for _, side, amount in bets if side != winner)
    return {user_id: amount + amount * lost // on_winner if side == winner else 0 for user_id, side, amount in bets}


def bank_line(bets, names):
    """names: {duelist id: name}."""
    if not bets:
        return kb.texts.bank_empty.format(max=MAX_BET)
    by_side = {side: 0 for side in names}
    for _, side, amount in bets:
        by_side[side] = by_side.get(side, 0) + amount
    parts = ", ".join(kb.texts.bank_side.format(name=names[side], amount=amount) for side, amount in by_side.items())
    return kb.texts.bank.format(total=sum(by_side.values()), parts=parts)


def settle_lines(bets, paid, names):
    """names: {telegram_id: name} of the bettors."""
    if not bets:
        return []
    lines = [kb.texts.bets_settled]
    for user_id, _, amount in bets:
        change = paid[user_id] - amount
        lines.append(f"{names[user_id]}: {'+' if change >= 0 else '−'}{abs(change)} {kb.theme_data.points}")
    return lines
