import json

from telegram_bots.bots.fat_joke.periodic_tasks import CURRENT_DISCIPLINE, CURRENT_DISCIPLINE_CODE

DEFAULT_IQ = 100
LEGACY_DISCIPLINE = "legacy"

iq_level_mapper = {
    0: ["Пускає слину...", "🤤"],
    71: ["Мавпа з гранатою", "🙊"],
    85: ["Homo Sapiens звичайний", "🙂"],
    116: ["Людина, якій черепушка жме :)", "🤓"],
    145: ["Мега мозок!", "🤯"],
    160: ["Кодзіма нервово курить...", "🤩"],
    500: ["Boss of the GYM!!!", "😈"],
}


def define_iq_levels(user_data):
    new_user_data = []
    data_to_print = []
    iq_int_levels = list(iq_level_mapper.keys())
    for u_data in user_data:
        iq_low_limit = 0
        for iq_level in iq_int_levels:
            if u_data[1] > iq_level:
                iq_low_limit = iq_level
        new_user_data.append((u_data[0], u_data[1], iq_level_mapper.get(iq_low_limit)))

    new_user_data = sorted(new_user_data, key=lambda x: -x[1])
    prize_places = {3: "🥉", 2: "🥈", 1: "🥇"}
    prizes_to_levels = {}
    places = 1
    for i in new_user_data:
        prize = prize_places.get(places, "")
        data_to_print.append(
            f"{prize}{i[0]} має рівень інтелекту: {i[1]}. \n{i[2][0]} -> {i[2][1]}\n=============================\n"
        )
        places += 1

    return "".join(data_to_print)


def init_answers_table(db):
    create_table_query = """
    CREATE TABLE IF NOT EXISTS Answers (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER NOT NULL,
        discipline TEXT NOT NULL,
        question_number INTEGER NOT NULL,
        is_correct INTEGER NOT NULL,
        answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (telegram_id, discipline, question_number)
    )
    """
    db.commit_query(create_table_query)

    # Users.questionare_done kept bare question numbers without a discipline,
    # so the old correct answers are moved over under a separate "legacy" discipline
    users_data = db.select_query("SELECT telegram_id, questionare_done FROM Users")
    for user_id, questionare_done in users_data:
        for question_number in json.loads(questionare_done or "[]"):
            db.commit_query(
                """
                INSERT OR IGNORE INTO Answers (telegram_id, discipline, question_number, is_correct)
                VALUES (?, ?, ?, 1)
                """,
                (user_id, LEGACY_DISCIPLINE, int(question_number)),
            )


def register_user(from_user, db):
    insert_user_query = """
    INSERT INTO Users (telegram_id, name, username, iq_level, questionare_done)
    SELECT ?, ?, ?, ?, '[]'
    WHERE NOT EXISTS (SELECT 1 FROM Users WHERE telegram_id = ?)
    """
    name = from_user.first_name or from_user.username or str(from_user.id)
    db.commit_query(insert_user_query, (from_user.id, name, from_user.username, DEFAULT_IQ, from_user.id))


def parse_answer_callback(callback_data):
    # "q <discipline> <question_number> <is_correct>", see make_answer_callback_data
    split_answer = callback_data.split(" ")
    if len(split_answer) != 4 or split_answer[0] != "q":
        return None
    _, discipline, question_number, is_correct = split_answer
    return discipline, int(question_number), is_correct == "1"


def get_user_iq_and_name(user_id, db):
    select_query_iq_level = """
        SELECT iq_level, name FROM Users WHERE telegram_id = ?
    """
    results = db.select_query(select_query_iq_level, (user_id,))
    user_iq_old = results[0][0]
    user_name = results[0][1]

    return user_iq_old, user_name


def calculate_id(user_iq_old, user_name, increase=False):
    if increase:
        user_iq_new = user_iq_old + 1
        message = f"""
        Твій рівень IQ підріс з {user_iq_old} до {user_iq_new}!
{user_name} розумнішає! 
Ай молодчинка :)
        """
    else:
        user_iq_new = user_iq_old - 1
        message = f"""
        Твій рівень IQ впав з {user_iq_old} до {user_iq_new}!
Ой-ой, {user_name} потроху тупіє :( 
Будеш ням-ням дімідрольчик?
        """

    return user_iq_new, message


def change_iq(user_id, user_iq_new, db):
    commit_query_iq_level = """
        UPDATE Users SET iq_level = ? WHERE telegram_id = ?
    """
    db.commit_query(commit_query_iq_level, (user_iq_new, user_id))


def save_answer(user_id, discipline, question_number, is_correct, db):
    """Returns False if the user has already answered this question, right or wrong."""
    insert_answer_query = """
    INSERT OR IGNORE INTO Answers (telegram_id, discipline, question_number, is_correct)
    VALUES (?, ?, ?, ?)
    """
    inserted_rows = db.commit_query(insert_answer_query, (user_id, discipline, question_number, int(is_correct)))
    return inserted_rows == 1


def get_anti_cheat_message(user_name):
    message = f"""
    Чітер в чаті!!! 
{user_name} хоче всіх нахлабучити і намагається відповісти на питання, на яке вже знає вірну відповідь!
От як тобі не соромно, GENIUS?
            """
    return message


def get_already_answered_questions(user_id, db):
    answered_questions_query = """
    SELECT question_number FROM Answers WHERE telegram_id = ? AND discipline = ? ORDER BY question_number
    """
    result = db.select_query(answered_questions_query, (user_id, CURRENT_DISCIPLINE_CODE))
    if not result:
        return "Ото лінива срака! На жодне питання ще не відповіли ("
    answer = ["Ви вже відповіли на наступні питання:\n"]
    for question_id in result:
        answer.append(f"{question_id[0]},")
    answer_string = "".join(answer)
    return answer_string


def get_quiz_leaders(db):
    select_leaders_query = """
    SELECT Users.name, COUNT(*) AS answers_count FROM Answers
    JOIN Users ON Users.telegram_id = Answers.telegram_id
    WHERE Answers.discipline = ? AND Answers.is_correct = 1
    GROUP BY Answers.telegram_id
    ORDER BY answers_count DESC
    LIMIT 3
    """
    result = db.select_query(select_leaders_query, (CURRENT_DISCIPLINE_CODE,))
    strings_to_print = [f"Лідери у дисципліні {CURRENT_DISCIPLINE}vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv\n"]
    for name, answers_count in result:
        string_to_print = f"{name}: {answers_count} вірних відповідей\n==============================\n"
        strings_to_print.append(string_to_print)

    return "".join(strings_to_print)
