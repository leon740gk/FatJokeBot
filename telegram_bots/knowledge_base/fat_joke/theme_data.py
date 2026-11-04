# MLBB setting for the loot in "Бам", ranks and achievements, BP are Battle Points

# a map objective that sometimes spawns under "Бам": (code, weight, BP, spawn line, taken line with {who})
loot_kinds = [
    ("red", 30, 5, "🔴 В джунглях появился Красный бафф!", "🔴 Красный бафф забрал(а) {who}"),
    ("blue", 30, 5, "🔵 В джунглях появился Синий бафф!", "🔵 Синий бафф забрал(а) {who}"),
    ("crab", 20, 8, "🦀 По реке ползёт краб!", "🦀 Краба разделал(а) {who}"),
    ("turtle", 15, 10, "🐢 Заспавнилась Черепаха!", "🐢 Черепаху добил(а) {who}"),
    ("lord", 5, 25, "🐉 ЛОРД ПРОСНУЛСЯ! Кто заберёт?", "🐉 Лорда забрал(а) {who}! Пушим базу!"),
]

# what the loot, achievements and bets give, BP are Battle Points
points = "BP"
loot_button = "⚔️ Забрать"
# quiz topic of the scheduled questions until an admin picks another with /discipline
default_discipline = "mlbb2"
# codes of the second rarest and the rarest loot, for the achievements and the summaries
rare_loot = "turtle"
top_loot = "lord"

# a press after someone else has taken it
late_phrases = [
    "Опоздал! Объект уже забрали 🐌",
    "Kill steal! Тебя опередили 😈",
    "Пока ты думал, его уже съели 🍗",
    "Минус объект, минус вечер 😭",
]

# nobody took it in time
gone_line = "💨 Объект ушёл в туман войны, никто не успел."
gone_phrase = "Объект уже ушёл, жди следующего спавна ⏳"

# (lowest BP, rank)
ranks = [
    (0, "🪖 Warrior"),
    (50, "🛡 Elite"),
    (120, "⚔️ Master"),
    (200, "🎖 Grandmaster"),
    (320, "💎 Epic"),
    (480, "🌟 Legend"),
    (700, "🔥 Mythic"),
    (1000, "👑 Mythical Glory"),
]

# code -> (emoji and name, how to get it); the conditions are in services/achievements.py
achievements = {
    "first_blood": ("🩸 First Blood", "первый верный ответ в викторине"),
    "double_kill": ("⚔️ Double Kill", "2 верных ответа подряд"),
    "triple_kill": ("🔥 Triple Kill", "3 верных ответа подряд"),
    "maniac": ("💀 Maniac", "4 верных ответа подряд"),
    "savage": ("👹 Savage", "5 верных ответов подряд"),
    "legendary": ("🧠 Legendary", "50 верных ответов в викторине"),
    "buff_hunter": ("🌿 Лесник", "забрать 10 объектов из «Бам»"),
    "turtle_hunter": ("🐢 Черепашатник", "забрать 3 Черепахи"),
    "lord_slayer": ("🐉 Убийца Лорда", "забрать Лорда"),
    "tank": ("🍩 Танк чата", "3 раза стать жиртрестом дня"),
    "teammate": ("🎮 Тиммейт", "зайти в 5 пати"),
    "mvp_quotes": ("📜 MVP цитатника", "3 своих цитаты в цитатнике"),
    "duelist": ("🤺 Дуэлянт", "выиграть 3 дуэли"),
    "night_farm": ("🦉 Ночной фарм", "написать в чат с 02:00 до 05:00 по Киеву"),
}

# {who} with @username, {name} of the achievement
unlocked_phrases = [
    "🏆 {who} открыл(а) достижение {name}!",
    "🏆 Новая медаль у {who}: {name}!",
    "🏆 {who} получает {name}! Респект 🫡",
]
