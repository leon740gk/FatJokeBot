import re

from telegram_bots.knowledge_base.chat_members import VALODYA

# misc stickers
froggy_sticker = "CAACAgIAAxkBAAPUZcvrZ2S53zFjRrjUOpAhgR4J4CEAAm0JAAIItxkCBbK_ShFrQjM0BA"
sergios_chair = "AgACAgIAAxkBAAIB-WXN55y__MRafzd2cTvFV25_LrhnAALc2TEbzp5wSrjxMe0rR402AQADAgADcwADNAQ"
heyhey = "CAACAgIAAx0CW-jr9QACciZlze6o7pwmCoG3SM2mT-arJ_SqLQACZzwAAiYi8Ettss0cMxi7hDQE"
joy = "CAACAgIAAxkBAAPQZcvnCyvE_jb2Cju0g2nHvEDb7_gAAkA5AAIer_BLAf5ZG1GHQZ00BA"
cunt = "CAACAgIAAxkBAAPSZcvolkf5M9vqwTYVo2TzUHJHlYkAAn83AAKf6HBJqpvoWKfSXlE0BA"
moshonochnye_klemmy = "CAACAgIAAxkBAAICAWXN9uK4bXzY6J5MN8EFu0Ifs7icAAJqPAACQ_GBSPrRIWVm7p8HNAQ"
raund = "CAACAgIAAxkBAAICcWXPTXcM0QrR5Zuk_GmXFITVNi1HAALZNwACvx9pSHgrvKDu231VNAQ"
valody_harosh_yalozyt = "CAACAgIAAxkBAAIB0WXNEebJkeOJ5TvL-Y2h6x782Cm3AAK8MwAC8KCpSbS5ZTJkBjTNNAQ"

# hentai
hentai_01 = "AgACAgIAAxkBAAICH2XOQKCVh2ZBZxQ6NOW54XkZhkPGAAIq3TEbzp5wSsISg3zKYLArAQADAgADcwADNAQ"
hentai_02 = "AgACAgIAAxkBAAICOGXOQ6K8d9ks81C5eqtwRWIUy3vdAAJN3TEbzp5wSlNcY4exffC6AQADAgADcwADNAQ"
hentai_03 = "AgACAgIAAxkBAAICOmXOQ_FZGwtZ54NPixmWxEBuXV13AAJO3TEbzp5wSn5Ceer5rulyAQADAgADcwADNAQ"
hentai_04 = "AgACAgIAAxkBAAICRmXOSDud0wph4ay-dJkWbyVN2gkwAAJh3TEbzp5wSkPsxSjq6-NMAQADAgADcwADNAQ"
hentai_05 = "AgACAgIAAxkBAAICSGXOSFrmHMLzyiUMFpl72g8GMb36AAJi3TEbzp5wSh769QO7yc6NAQADAgADcwADNAQ"
hentai_06 = "AgACAgIAAxkBAAICSmXOSH5B38DEv_Sfw3p7yNOQhAiLAAJj3TEbzp5wSkT9cf5ZkQlyAQADAgADcwADNAQ"
hentai_07 = "AgACAgIAAxkBAAICTGXOSJaiVl4SJCxZJEzm9aybfSyOAAJm3TEbzp5wSiDBfLtqmnfvAQADAgADcwADNAQ"
hentai_08 = "AgACAgIAAxkBAAICe2XPWLuB_d3gImLvy3WXJ-mRXSrXAALz1zEbj1-BSu06ASKz7kEMAQADAgADcwADNAQ"
hentai_09 = "AgACAgIAAxkBAAICfWXPWNv3OtSIsZuIGN8cwU3gwbr6AAL01zEbj1-BSi_3Q72oAfTvAQADAgADcwADNAQ"
hentai_10 = "AgACAgIAAxkBAAICf2XPWOtPEUG-JdjJioibEdq0c0LNAAL11zEbj1-BSmv7hmRyYqseAQADAgADcwADNAQ"
hentai_11 = "AgACAgIAAxkBAAICgWXPWPjL8efjfLys9JRQGrXnbO_PAAL21zEbj1-BSuPmsrIxPKjNAQADAgADcwADNAQ"
hentai_12 = "AgACAgIAAxkBAAICg2XPWQhA9_qiF3lpYshN6m0IarlOAAL41zEbj1-BSrJJezqtp0PGAQADAgADcwADNAQ"
hentai_13 = "AgACAgIAAxkBAAIChWXPWRViIp4s3HkVgRbrvvcCvFGRAAL51zEbj1-BSlNWUF_5gbf9AQADAgADcwADNAQ"
hentai_14 = "AgACAgIAAxkBAAICh2XPWSI9NWpJvJ17UZeEpqsn3aPQAAL61zEbj1-BSjfwU0kjQ4TmAQADAgADcwADNAQ"
hentai_15 = "AgACAgIAAxkBAAICiWXPWS7JaxXWQQXBAdeohHDuf6iRAAL81zEbj1-BSvxAr-6LffacAQADAgADcwADNAQ"

hentai_collection = [
    hentai_01,
    hentai_02,
    hentai_03,
    hentai_04,
    hentai_05,
    hentai_06,
    hentai_07,
    hentai_08,
    hentai_09,
    hentai_10,
    hentai_11,
    hentai_12,
    hentai_13,
    hentai_14,
    hentai_15,
]

sticker_responses = [
    "Опа, стикер! ))",
    "Харош )",
    "Нужно больше стикеров! (с)",
    "Так, а де ж внєзапний???",
    "Ну нормуль.",
    "Це не прикольно.",
    "Ой все.",
    "Харош засирать чат.",
]

sergios_rules = [
    "10 правил Серджіо. Правило 1. Ніколи не ображайся, але роби висновки!",
    "10 правил Серджіо. Правило 2. Ігноруй всіх, але рахуй стікери!",
    "10 правил Серджіо. Правило 3. Похудати ніколи не пізно, але краще потім якось!",
    "10 правил Серджіо. Правило 4. Халвінг - то вам не лістінг!",
    "10 правил Серджіо. Правило 5. Кібербулінг - він повсюду! Остерігайтеся!",
    "10 правил Серджіо. Правило 6. Статистика - то круто!",
    "10 правил Серджіо. Правило 7. Якщо одні двері закрились, інші - обов'язково відкриються. Ніколи не купляй Ниву.",
    "10 правил Серджіо. Правило 8. 5 км бігу - то сила! Але 3 булочки - краще)",
    "10 правил Серджіо. Правило 9. Завжди є загноблені, а є недоторкані! О блядський смисл життя, якщо ти єсць!",
    "10 правил Серджіо. Правило 10. Все - це коли батюшка із-за столу встав!",
]

volodymyr_rules = [
    "3 заповіді Валоді. Заповідь 1. Жизь хуйовая.",
    "3 заповіді Валоді. Заповідь 2. Айфон - хуйня.",
    "3 заповіді Валоді. Заповідь 3. Пить - то западло.",
]

text_to_text_reactions = {
    ("сірожа", "серий", "сергій", "сіроня", "сережа", "серега", "серёга"): sergios_rules,
    ("вова", "валодя", "володя"): volodymyr_rules,
    ("влад", "slave"): "@What_i6_Love What is love? Baby don't hurt me!",
    ("кабачок",): "@Momento0_0_7 Кабачок, ти 2 неділі YappyDoor :)",
    ("саня",): "Boss of the GYM!",
    ("жах", "кошмар"): "@Mirai_Nova Кошмара, де стріми???",
    ("сучка", "сучку", "сучечка"): "Сучка в чаті тільки одна )) гаф-гаф",
    ("лікарня", "палата", "дурка", "дурдом"): "Край родной, навєк любімий!",
}

photo_to_text_reactions = {("тренажер",): sergios_chair}

sticker_to_text_reactions = {
    ("кайф", "каеф"): joy,
    ("крінж", "кринж"): cunt,
    ("певень", "питух", "петух", "півень"): heyhey,
    ("фашист", "фашик", "адик", "адік", "адольф"): moshonochnye_klemmy,
    ("раунд",): raund,
}

special_sticker_responses = {
    "AgAD2UMAAuk2EUo": ["Курс Защекоина (с) растет!!!", "ZashceCoin (с) to the 'Withcer'!!!"],
    "AgADED4AAq-5MUo": ["Опа! Основной эмитент новой криптовалюты :)", "Listing and halving!!!", "Try my tools :)"],
}

regex_reactions = {re.compile("\d{3}([.,])?(\d{3})?.*"): "Сергійко збирає на тренажер!"}


to_person_reactions = {VALODYA: valody_harosh_yalozyt}