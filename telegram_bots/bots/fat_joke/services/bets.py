from telegram_bots.bots.fat_joke.db import bets as bets_db

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
        return "Ставки принимаются, только пока вызов не принят ⏳"
    if user_id in (current.challenger, current.opponent):
        return "Дуэлянтам ставить нельзя, это договорняк 😏"
    if side not in (current.challenger, current.opponent):
        return "Этот человек не участвует в дуэли"
    if amount < 1:
        return "Ставка должна быть хотя бы 1 BP"
    placed = bets_db.get(db, current.id, user_id)
    if placed and placed[0] != side:
        return "Ты уже поставил(а) на другого, переобуваться нельзя 👟"
    if (placed[1] if placed else 0) + amount > MAX_BET:
        return f"Не больше {MAX_BET} BP на одну дуэль"
    if amount > balance:
        return f"Не хватает BP: у тебя {balance} BP"
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
        return f"💰 Ставок пока нет. Кнопки ниже или /bet <сумма> @ник, до {MAX_BET} BP"
    by_side = {side: 0 for side in names}
    for _, side, amount in bets:
        by_side[side] = by_side.get(side, 0) + amount
    parts = ", ".join(f"на {names[side]} {amount}" for side, amount in by_side.items())
    return f"💰 Банк: {sum(by_side.values())} BP ({parts})"


def settle_lines(bets, paid, names):
    """names: {telegram_id: name} of the bettors."""
    if not bets:
        return []
    lines = ["💰 Ставки:"]
    for user_id, _, amount in bets:
        change = paid[user_id] - amount
        lines.append(f"{names[user_id]}: {'+' if change >= 0 else '−'}{abs(change)} BP")
    return lines
