IQ_LEVELS = {
    0: ["Пускает слюни...", "🤤"],
    71: ["Обезьяна с гранатой", "🙊"],
    85: ["Homo Sapiens обыкновенный", "🙂"],
    116: ["Человек, которому черепушка жмёт :)", "🤓"],
    145: ["Мега мозг!", "🤯"],
    160: ["Кодзима нервно курит...", "🤩"],
    500: ["Boss of the GYM!!!", "😈"],
}
PRIZES = {1: "🥇", 2: "🥈", 3: "🥉"}


def level_for(iq_level):
    low_limit = max((limit for limit in IQ_LEVELS if iq_level >= limit), default=0)
    return IQ_LEVELS[low_limit]


def format_iq_table(rows):
    lines = []
    for place, (name, iq_level) in enumerate(sorted(rows, key=lambda row: -row[1]), start=1):
        title, emoji = level_for(iq_level)
        lines.append(
            f"{PRIZES.get(place, '')}{name} имеет уровень интеллекта: {iq_level}. \n"
            f"{title} -> {emoji}\n=============================\n"
        )
    return "".join(lines)


def change_message(iq_old, user_name, increase):
    if increase:
        iq_new = iq_old + 1
        message = f"""
        Твой уровень IQ вырос с {iq_old} до {iq_new}!
{user_name} умнеет!
Ай молодчинка :)
        """
    else:
        iq_new = iq_old - 1
        message = f"""
        Твой уровень IQ упал с {iq_old} до {iq_new}!
Ой-ой, {user_name} понемногу тупеет :(
Будешь ням-ням димедрольчик?
        """
    return iq_new, message


def anti_cheat_message(user_name):
    return f"""
    Читер в чате!!!
{user_name} хочет всех надурить и пытается ответить на вопрос, на который уже знает верный ответ!
Вот как тебе не стыдно, GENIUS?
            """
