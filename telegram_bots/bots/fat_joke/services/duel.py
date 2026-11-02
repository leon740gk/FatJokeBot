import random
from dataclasses import dataclass

from telegram_bots.bots.fat_joke.services import quiz

PRIZE = 10
# the challenge waits this long for an answer, the question this long for both duelists
ACCEPT_MINUTES = 10
ANSWER_SECONDS = 120
ACCEPT = "yes"
DECLINE = "no"


@dataclass(frozen=True)
class Duel:
    id: int
    chat_id: int
    message_id: int | None
    challenger: int
    opponent: int
    discipline: str | None
    question_number: int | None
    status: str
    started_at: float | None
    challenger_option: int | None
    challenger_seconds: float | None
    opponent_option: int | None
    opponent_seconds: float | None

    def side_of(self, user_id):
        if user_id == self.challenger:
            return "challenger"
        if user_id == self.opponent:
            return "opponent"
        return None

    def both_answered(self):
        return self.challenger_option is not None and self.opponent_option is not None


def from_row(row):
    return Duel(*row) if row else None


def challenge_callback(duel_id, answer):
    return f"duel {answer} {duel_id}"


def answer_callback(duel_id, option_index):
    return f"duel a {duel_id} {option_index}"


def parse_callback(data):
    """("yes" | "no", duel id, None) or ("a", duel id, option index); None for anything else."""
    parts = (data or "").split(" ")
    if len(parts) == 3 and parts[0] == "duel" and parts[1] in (ACCEPT, DECLINE) and parts[2].isdigit():
        return parts[1], int(parts[2]), None
    if len(parts) == 4 and parts[0] == "duel" and parts[1] == "a" and parts[2].isdigit() and parts[3].isdigit():
        return "a", int(parts[2]), int(parts[3])
    return None


def challenge_text(challenger, opponent, discipline=None):
    topic = f" по теме {quiz.title(discipline)}" if discipline else ""
    return (
        f"⚔️ {challenger} вызывает {opponent} на дуэль{topic}!\n\n"
        f"Один вопрос на двоих. Кто ответит правильно и быстрее, забирает {PRIZE} BP.\n"
        f"У {opponent} есть {ACCEPT_MINUTES} минут, чтобы принять вызов."
    )


def pick_question(discipline=None, rng=random):
    discipline = discipline or rng.choice(list(quiz.DISCIPLINES))
    return quiz.get_question(discipline, rng.choice(list(quiz.DISCIPLINES[discipline].questions)))


def render(question, duel_id, challenger, opponent, rng=random):
    """The quiz question with buttons that answer the duel, not the quiz."""
    rendered = quiz.render_question(question, rng)
    rows = [
        [(label, answer_callback(duel_id, quiz.parse_callback(data).option_index)) for label, data in row]
        for row in rendered.rows
    ]
    header = f"⚔️ Дуэль: {challenger} vs {opponent}\n⏱ {ANSWER_SECONDS} секунд, отвечают только дуэлянты\n\n"
    return quiz.RenderedQuestion(header + rendered.text, rows)


def winner_of(duel, question):
    """telegram_id of the winner, None for a draw: right beats wrong, then the faster one."""
    results = []
    for user_id, option, seconds in (
        (duel.challenger, duel.challenger_option, duel.challenger_seconds),
        (duel.opponent, duel.opponent_option, duel.opponent_seconds),
    ):
        if option is not None and option in question.correct:
            results.append((seconds, user_id))
    if not results:
        return None
    results.sort()
    if len(results) == 2 and results[0][0] == results[1][0]:
        return None
    return results[0][1]


def answer_line(name, option, seconds, question):
    if option is None:
        return f"😴 {name} не успел(а) ответить"
    mark = "✅" if option in question.correct else "❌"
    seconds_text = f"{seconds:.1f}".replace(".", ",")
    return f"{mark} {name}: {question.options[option]} ({seconds_text} с)"


def result_text(duel, question, names, winner):
    """names: {telegram_id: name with @username}."""
    lines = [
        f"⚔️ Дуэль: {names[duel.challenger]} vs {names[duel.opponent]}",
        f"{quiz.title(question.discipline)}. {question.text}",
        "",
        answer_line(names[duel.challenger], duel.challenger_option, duel.challenger_seconds, question),
        answer_line(names[duel.opponent], duel.opponent_option, duel.opponent_seconds, question),
        "",
        quiz.answer_details(question),
        "",
    ]
    if winner:
        lines.append(f"🏆 Побеждает {names[winner]}! +{PRIZE} BP")
    else:
        lines.append("🤝 Ничья, BP остаются при своих.")
    return "\n".join(lines)
