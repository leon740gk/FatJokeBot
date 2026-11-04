# Gaming setting for the loot in "Бам", ranks and achievements: people in the chat play different games,
# so nothing here belongs to one game. XP are what the loot, achievements and bets give.

points = "XP"

# drop that sometimes falls under "Бам": (code, weight, XP, spawn line, taken line with {who})
loot_kinds = [
    ("common", 30, 5, "⚪ Випав звичайний дроп!", "⚪ Звичайний дроп забрав(ла) {who}"),
    ("uncommon", 30, 5, "🟢 Випав незвичайний дроп!", "🟢 Незвичайний дроп забрав(ла) {who}"),
    ("rare", 20, 8, "🔵 Випав рідкісний дроп!", "🔵 Рідкісний дроп забрав(ла) {who}"),
    ("epic", 15, 10, "🟣 Випав епічний дроп!", "🟣 Епічний дроп забрав(ла) {who}"),
    ("legendary", 5, 25, "🟡 ЛЕГЕНДАРНИЙ ДРОП! Хто встигне?", "🟡 Легендарний дроп забрав(ла) {who}! Оце лак!"),
]

loot_button = "🎁 Забрати"
# codes of the second rarest and the rarest drop, for the achievements and the summaries
rare_loot = "epic"
top_loot = "legendary"
# quiz topic of the scheduled questions until an admin picks another with /discipline
default_discipline = "ukr"

# a press after someone else has taken it
late_phrases = [
    "Запізно! Дроп уже забрали 🐌",
    "Kill steal! Тебе випередили 😈",
    "Поки ти думав, лут уже в чужому інвентарі 🎒",
    "Мінус дроп, мінус вечір 😭",
]

# nobody took it in time
gone_line = "💨 Дроп зник, ніхто не встиг підібрати."
gone_phrase = "Дроп уже зник, чекай на наступний ⏳"

# (lowest XP, rank)
ranks = [
    (0, "🐣 Noob"),
    (50, "🎮 Casual"),
    (120, "🕹 Gamer"),
    (200, "🎯 Tryhard"),
    (320, "💪 Pro"),
    (480, "💎 Elite"),
    (700, "🌟 Legend"),
    (1000, "👑 GOAT"),
]

# code -> (emoji and name, how to get it); the codes and conditions are in engine/services/achievements.py
achievements = {
    "first_blood": ("🩸 Перша кров", "перша правильна відповідь у вікторині"),
    "double_kill": ("⚔️ Комбо x2", "2 правильні відповіді поспіль"),
    "triple_kill": ("🔥 Комбо x3", "3 правильні відповіді поспіль"),
    "maniac": ("💀 Комбо x4", "4 правильні відповіді поспіль"),
    "savage": ("👹 Нестримний", "5 правильних відповідей поспіль"),
    "legendary": ("🧠 Енциклопедист", "50 правильних відповідей у вікторині"),
    "buff_hunter": ("🎁 Лутер", "забрати 10 дропів з «Бам»"),
    "turtle_hunter": ("🟣 Епічний мисливець", "забрати 3 епічні дропи"),
    "lord_slayer": ("🟡 Легенда дропу", "забрати легендарний дроп"),
    "tank": ("🍩 Танк чату", "3 рази стати жиртрестом дня"),
    "teammate": ("🎮 Тімейт", "зайти в 5 загонів"),
    "mvp_quotes": ("📜 MVP цитатника", "3 свої цитати в цитатнику"),
    "duelist": ("🤺 Дуелянт", "виграти 3 дуелі"),
    "night_farm": ("🦉 Нічний задрот", "написати в чат з 02:00 до 05:00 за Києвом"),
}

# {who} with @username, {name} of the achievement
unlocked_phrases = [
    "🏆 {who} відкриває досягнення {name}!",
    "🏆 Нове досягнення у {who}: {name}!",
    "🏆 {who} отримує {name}! Респект 🫡",
]
