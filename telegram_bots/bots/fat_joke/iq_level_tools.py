import json

iq_level_mapper = {
    0: "Пускає слину...",
    71: "Мавпа з гранатою",
    85: "Homo Sapiens звичайний",
    116: "Людина, якій черепушка жме :)",
    145: "Мега мозок!",
    160: "Кодзіма нервово курить...",
    500: "Boss of the GYM!!!",
}


def define_iq_levels(user_data, iq_level_mapper):
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
    for i in new_user_data:
        data_to_print.append(f"{i[0]} має рівень інтелекту: {i[1]}. {i[2]}\n==============\n")

    return "".join(data_to_print)


def get_user_iq_and_name(user_id, db):
    select_query_iq_level = f"""
        SELECT iq_level, name FROM Users WHERE telegram_id = {user_id}
    """
    results = db.select_query(select_query_iq_level)
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
    commit_query_iq_level = f"""
        UPDATE Users SET iq_level = {user_iq_new} WHERE telegram_id = {user_id}
    """
    db.commit_query(commit_query_iq_level)


def did_user_answer_this_question(user_id, question_number, db):
    select_questions_query = f"""
    SELECT questionare_done from Users WHERE telegram_id = {user_id}
    """
    result = json.loads(db.select_query(select_questions_query)[0][0])
    if question_number not in result:
        result.append(question_number)
        new_result = json.dumps(result)
        update_question_query = f"""
        UPDATE Users SET questionare_done = '{new_result}' WHERE telegram_id = {user_id}
        """
        db.commit_query(update_question_query)
        return False
    return True


def get_anti_cheat_message(user_name):
    message = f"""
    Чітер в чаті!!! 
{user_name} хоче всіх нахлабучити і намагається відповісти на питання, на яке вже знає вірну відповідь!
От як тобі не соромно, GENIUS?
            """
    return message


def get_already_answered_questions(user_id, db):
    answered_questions_query = f"""
    SELECT questionare_done FROM Users WHERE telegram_id = {user_id}
    """
    result = db.select_query(answered_questions_query)[0][0]
    result_raw = json.loads(result)
    if not result_raw:
        return "Ото лінива срака! На жодне питання ще не відповіли ("
    result = [int(i) for i in result_raw]
    result.sort()
    answer = ["Ви вже відповіли на наступні питання:\n"]
    for question_id in result:
        answer.append(f"{question_id},")
    answer_string = "".join(answer)
    return answer_string
