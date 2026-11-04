# What the bot says outside of the jokes: buttons, answers to commands, summaries.
# {names} in braces are filled in by the engine (telegram_bots/engine); word forms are (1, 2-4, 5+) for plural().
# The same names as in knowledge_base/fat_joke/texts.py, telegram_bots/tests/test_content.py checks it.

# /me and /ranks
rank_up = "⬆️ {who} піднімається до рангу {rank}!"
profile_rank = "🏅 Ранг: {rank}, {points} XP"
profile_next_rank = "   до {rank}: ще {points} XP"
profile_answers = "✅ Правильних відповідей: {correct}, найкраща серія: {streak}"
profile_loot = "🎁 Дропу з «Бам»: {count}"
profile_top_loot = ", з них легендарного: {count}"
profile_fat_days = "🍩 Жиртрест дня: {count} {times}"
profile_parties = "🎮 Загонів: {count}"
profile_duels = "🤺 Перемог у дуелях: {count}"
profile_achievements = "Досягнення {have}/{total}:"
profile_locked = "\nЩе закриті:"
ranks_empty = "Рейтинг поки порожній. Ловіть дроп у «Бам» 🎁"
ranks_title = "🏆 Рейтинг чату за XP:\n"
ranks_footer = "\nСвій профіль: /me"

# duel bets, /bet
bet_too_late = "Ставки приймаються, лише поки виклик не прийнято ⏳"
bet_by_duelist = "Дуелянтам ставити не можна, це договірняк 😏"
bet_on_outsider = "Ця людина не бере участі в дуелі"
bet_too_small = "Ставка має бути хоча б 1 XP"
bet_other_side = "Ти вже поставив(ла) на іншого, перевзуватися не можна 👟"
bet_too_big = "Не більше {max} XP на одну дуель"
bet_no_money = "Не вистачає XP: у тебе {balance} XP"
bank_empty = "💰 Ставок поки немає. Кнопки нижче або /bet <сума> @нік, до {max} XP"
bank_side = "на {name} {amount}"
bank = "💰 Банк: {total} XP ({parts})"
bets_settled = "💰 Ставки:"

# duels, /duel
duel_topic = " на тему {topic}"
duel_challenge = (
    "⚔️ {challenger} викликає {opponent} на дуель{topic}!\n\n"
    "Одне питання на двох. Хто відповість правильно і швидше, забирає {prize} XP.\n"
    "У {opponent} є {minutes} хвилин, щоб прийняти виклик."
)
duel_title = "⚔️ Дуель: {challenger} vs {opponent}"
duel_question = "⚔️ Дуель: {challenger} vs {opponent}\n⏱ {seconds} секунд, відповідають лише дуелянти\n\n"
duel_no_answer = "😴 {name} не встиг(ла) відповісти"
duel_answer = "{mark} {name}: {option} ({seconds} с)"
duel_winner = "🏆 Перемагає {winner}! +{prize} XP"
duel_draw = "🤝 Нічия, XP залишаються при своїх."
duel_expired = "⌛ {opponent} так і не прийняв(ла) виклик {challenger}. Злякався(лася)?"

# IQ from the quiz, /show_iq; lowest IQ -> [title, emoji]
iq_levels = {
    0: ["Застряг у туторіалі...", "🤤"],
    71: ["Бот на легкому рівні складності", "🙊"],
    85: ["Звичайний NPC", "🙂"],
    116: ["Проходить без гайдів :)", "🤓"],
    145: ["Мегамозок!", "🤯"],
    160: ["Кодзіма нервово курить...", "🤩"],
    500: ["Фінальний бос!!!", "😈"],
}
iq_row = "{prize}{name} має рівень інтелекту: {iq}. \n{title} -> {emoji}\n=============================\n"
iq_up = "Твій рівень IQ виріс з {old} до {new}!\n{name} розумнішає!\nОт молодчинка :)"
iq_down = "Твій рівень IQ впав з {old} до {new}!\nОй-ой, {name} потроху тупішає :(\nМоже, кави?"
anti_cheat = (
    "Читер у чаті!!!\n"
    "{name} хоче всіх надурити і намагається відповісти на питання, на яке вже знає правильну відповідь!\n"
    "Ну як тобі не соромно, GENIUS?"
)

# "Жиртрест дня", /fatstats
times_forms = ("раз", "рази", "разів")
fat_stats_empty = "Жиртрестів ще не було. Виправимо: /fat 🍩"
fat_stats_title = "🍔 Зала слави жиртрестів:\n"

# the loot under "Бам"
loot_first_takes = "Хто перший натисне, той і забере: +{points} XP"

# /members
members_present = "👥 У чаті ({count}):"
members_gone = "\n🚪 Пішли ({count}):"
members_footer = "\nХто жодного разу не писав при боті, з'явиться тут після першого повідомлення."

# /party
party_title = "🎮 Збираємо загін!"
party_count = "\nУ ділі {count}/{size}:"
party_gathered = "\n✅ Загін зібрано!"
party_expired = "\n💨 Не зібралися за {hours} години. Новий загін: /party"
party_join_hint = "\nТисни «Я в ділі» 👇"
party_call = " — загін зібрано, заходимо в гру! 🎮"

# the quiz
question_forms = ("питання", "питання", "питань")
quiz_limit = (
    "На сьогодні все: {limit} {questions} на день 🧠🔥\n"
    "Мозку потрібен відпочинок, нові питання — завтра з 00:00 за Києвом."
)
quiz_pick_topic = "Яку тему хочете? 👇"
quiz_right_answer = "Правильна відповідь: {answer}"
quiz_expired = "⏰ Час вийшов, ніхто не відповів!"
answered_none = "Ото лінива срака! Ще на жодне питання не відповіли ("
answered_title = "Ви вже відповіли на такі питання:\n"
leaders_title = "Лідери в темі {topic}, сезон {season}\nvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv\n"
leaders_row = "{name}: {count} правильних відповідей\n==============================\n"
all_leaders_title = "🏆 Лідери вікторини за темами, поточні сезони"
all_leaders_topic = "\n{topic}, сезон {season}:"
all_leaders_empty = "\nПоки без лідерів: {topics}"
all_leaders_footer = "\nЗіграти: /quiz"
season_end = "🏁 Сезон {season} у темі {topic} завершено! Питання закінчилися.\n"
season_winners = "Переможці:\n"
season_no_winners = "Переможців немає, ніхто не відповів правильно (\n"
season_next = "\nПочинаємо сезон {season}!"
disciplines_title = "Теми вікторини:\n"
disciplines_row = "{marker}{code}: {title} ({count} {questions})\n"
disciplines_footer = (
    "\nПитання на будь-яку тему: /quiz <тема>, наприклад /quiz мова"
    "\nЗмінити тему питань за розкладом (лише адміни чату): /discipline <тема>"
)

# "we miss you" roll call of the inactive
day_forms = ("день", "дні", "днів")
miss_you_title = "Увага! Увага!\nНаш бот розшукує зниклих безвісти!\n"
miss_you_row = "{name} @{username}, про тебе ми не чули вже {days} {days_word} :(\n"
miss_you_footer = "Бот і весь чат сумують за вами...\nНапишіть, як у вас справи.\nЧекаємо на вас :)"

# the weekly summary, /week
message_forms = ("повідомлення", "повідомлення", "повідомлень")
right_answer_forms = ("правильна відповідь", "правильні відповіді", "правильних відповідей")
week_title = "📅 Підсумки тижня {first} – {last}"
week_talkers = "💬 Балакуни тижня:"
week_total = "Усього в чаті: {count} {messages}"
week_brains = "🧠 Мізки тижня:"
week_farmers = "🎁 Фармери тижня:"
week_top_loot = ", легендарного: {count}"
week_fatties = "🍩 Жиртрести тижня: {names}"
week_medals = "🏆 Нові досягнення:"
week_parties = "🎮 Зібрано загонів: {count}"
week_quote = "📜 Цитата тижня"
week_silent = "🦗 Мовчуни тижня: {names}. Ми сумуємо, напишіть хоч щось!"
week_mvp = "👑 MVP тижня: {name}!"
week_quiet = "Тихий тиждень... Навіть жиртреста ніхто не вирахував. Виправляйтеся: /fat /quiz /party 🙃"

# "Хто з нас…" poll results
vote_forms = ("голос", "голоси", "голосів")
who_no_votes = "🗳 «{question}»\n\nНіхто не проголосував 😴 Мабуть, усі одразу зрозуміли, про кого мова."
who_result = "🗳 «{question}»\n\nНа думку чату, це "
who_and = " і "
who_shared = ", ділять титул порівну 🤝"

# quiz and other commands
chat_id = "ID цього чату: {id}"
unknown_topic = "Не знаю такої теми 🤔\n\n"
own_question_first = "Спершу відповідай на своє питання 👆"
discipline_admins_only = "Змінювати тему можуть лише адміни чату 😈"
discipline_set = "Тепер питання за розкладом на тему {topic}! Наступне питання: /quiz"

# duel and bet commands and buttons
duel_how_to = (
    "Кого викликаєш? Відповідай /duel на повідомлення суперника або напиши /duel @нік "
    "(можна з темою: /duel @нік мова)"
)
duel_unknown_person = "Не знаю такої людини в чаті 🤔"
duel_self = "Дуель із самим собою? Це вже шизофренія 🙃"
duel_busy_you = "У тебе вже є незакінчена дуель ⚔️"
duel_busy_opponent = "У суперника вже є незакінчена дуель ⚔️"
duel_accept_button = "⚔️ Прийняти"
duel_decline_button = "🏳️ Відмовитися"
bet_button = "💰 +{stake} на {name}"
duel_over = "Ця дуель уже закінчилася"
bet_taken = "Ставку прийнято! Усього {total} XP 💰"
bet_how_to = (
    "Ставки на дуелі: /bet <сума> @нік, наприклад /bet 20 @alex, до {max} XP.\n"
    "Ставити можна, поки виклик не прийнято. Або тисни кнопки під викликом 💰"
)
bet_no_duel = "У {name} зараз немає дуелі, на яку можна поставити 🤷"
bet_placed = "💰 {who} ставить {amount} XP на {name}!"
duel_stale = "Виклик уже не актуальний"
duel_cancelled = "🏳️ {name} скасував(ла) виклик."
duel_declined = "🏳️ {name} відмовився(лася) від дуелі."
bets_refunded = "\n💰 Ставки повернули."
duel_not_you = "Це не тебе викликали 🍿"
duel_go = "Погнали! ⚔️"
duel_watch_only = "Ти не береш участі в цій дуелі, просто дивись 🍿"
duel_already_answered = "Ти вже відповів(ла), чекаємо на суперника ⏳"
duel_answer_taken = "Відповідь прийнято, чекаємо на суперника ⏳"

# admin commands
group_only = "Ця команда працює лише в групі 👥"
members_admins_only = "Перевіряти учасників можуть лише адміни чату 😈"

# party buttons
party_dead = "Цей загін уже не працює, збери новий: /party"
party_join_button = "✅ Я в ділі"
party_leave_button = "❌ Виходжу"
party_already_open = "Загін уже збирається, тисни кнопку тут 👆"
party_already_gathered = "Загін уже зібрано 🎮"
party_already_in = "Ти вже в загоні 😉"
party_joined = "Ти в ділі! 🎮"
party_not_in = "Тебе й так немає в загоні 🤷"
party_left = "Ти вийшов(ла) із загону"

# quiz buttons
topic_button_dead = "Ця кнопка вже не працює, напишіть /quiz"
topic_not_yours = "Це не твій /quiz 😉 Виклич свій: /quiz"
topic_taken = "Тему вже вибрали"
own_question_above = "Спершу відповідай на своє питання, воно вище 👆"
question_closed = "Це питання вже закрите"
question_not_yours = "Злодюжка! 😈 Це питання для {name}. Виклич своє: /quiz"

# quote book, /save and /quote
quote_book_empty = "Цитатник поки порожній 📭\nВідповідай командою /save на смішне повідомлення, і воно потрапить сюди."
save_how_to = "Відповідай командою /save на повідомлення, яке треба увічнити 📜"
save_text_only = "До цитатника потрапляє лише текст 🤷"
unknown_author = "Невідомий геній"
quote_already_saved = "Ця цитата вже в цитатнику 📜"
quote_saved = "Збережено в цитатник 📜 Усього цитат: {count}"
quote_none_of = "У «{author}» цитат поки немає 🤔"
quote_of_the_day = "📜 Цитата дня"

# /who
who_already_open = "Опитування вже триває, голосуй тут 👆"
who_not_enough = "Для опитування потрібно хоча б двоє знайомих боту людей у чаті 🤷"

# birthdays, /birthday and /birthdays
year_forms = ("рік", "роки", "років")
birthday_how_to = (
    "Указати свій день народження: /birthday 03.05 або з роком /birthday 03.05.1990\n"
    "Адмін може вказати за іншого: відповісти /birthday 03.05 на його повідомлення. Забути дату: /birthday -"
)
birthday_known = "🎂 День народження {name}: {date}"
birthday_unknown = "🎂 Дня народження поки не знаю."
birthday_saved = "🎂 Запам'ятав: {name} святкує {date}. Зранку того дня привітаємо!"
birthday_forgotten = "🗑 Забув день народження {name}."
birthday_bad_date = "Не схоже на дату 🤔"
birthday_admins_only = "Указувати день народження за інших можуть лише адміни чату 😈"
birthdays_empty = "Жодного дня народження поки не знаю 🤷\nУкажи свій: /birthday 03.05"
birthdays_title = "🎉 Найближчі дні народження:\n"
birthdays_today = "сьогодні!"
birthdays_in = "через {days} {days_word}"
birthdays_footer = "\nДодати свій: /birthday 03.05"
birthday_age = " — {age} {years}!"
birthday_openers = [
    "🎉 Увага, чат! Сьогодні день народження!",
    "🥳 Бам! Сьогодні в нас іменинник!",
    "💀⚙️ Серво-череп фіксує свято: сьогодні день народження!",
]
birthday_wishes = [
    "Вітаємо! Здоров'я, грошей, перемог у кожній катці і щоб лаги оминали стороною 🎮",
    "З днем народження! Нехай IQ росте, а пінг — навпаки 🎂",
    "Вітаємо! Легендарного дропу щодня і тімейтів, які не підводять 🎁",
    "З днем народження! Бажаємо рангу Legend у житті, а не лише в грі 🏆",
]

# gaming news, /news
news_title = "🎮 Ігрові новини, {date}"
news_empty = "Свіжих новин поки немає, все вже було 📰"
news_off = "Новини в цього бота вимкнені 📰"
