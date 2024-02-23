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
