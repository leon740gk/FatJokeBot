IQ_LEVELS = {
    0: ["Пускає слину...", "🤤"],
    71: ["Мавпа з гранатою", "🙊"],
    85: ["Homo Sapiens звичайний", "🙂"],
    116: ["Людина, якій черепушка жме :)", "🤓"],
    145: ["Мега мозок!", "🤯"],
    160: ["Кодзіма нервово курить...", "🤩"],
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
            f"{PRIZES.get(place, '')}{name} має рівень інтелекту: {iq_level}. \n"
            f"{title} -> {emoji}\n=============================\n"
        )
    return "".join(lines)


def change_message(iq_old, user_name, increase):
    if increase:
        iq_new = iq_old + 1
        message = f"""
        Твій рівень IQ підріс з {iq_old} до {iq_new}!
{user_name} розумнішає! 
Ай молодчинка :)
        """
    else:
        iq_new = iq_old - 1
        message = f"""
        Твій рівень IQ впав з {iq_old} до {iq_new}!
Ой-ой, {user_name} потроху тупіє :( 
Будеш ням-ням дімідрольчик?
        """
    return iq_new, message


def anti_cheat_message(user_name):
    return f"""
    Чітер в чаті!!! 
{user_name} хоче всіх нахлабучити і намагається відповісти на питання, на яке вже знає вірну відповідь!
От як тобі не соромно, GENIUS?
            """
