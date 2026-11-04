# What the bot says outside of the jokes: buttons, answers to commands, summaries.
# {names} in braces are filled in by the engine (telegram_bots/engine); word forms are (1, 2-4, 5+) for plural().

# /me and /ranks
rank_up = "⬆️ {who} поднимается до ранга {rank}!"
profile_rank = "🏅 Ранг: {rank}, {points} BP"
profile_next_rank = "   до {rank}: ещё {points} BP"
profile_answers = "✅ Верных ответов: {correct}, лучшая серия: {streak}"
profile_loot = "⚔️ Объектов из «Бам»: {count}"
profile_top_loot = ", из них Лордов: {count}"
profile_fat_days = "🍩 Жиртрест дня: {count} {times}"
profile_parties = "🎮 Пати: {count}"
profile_duels = "🤺 Побед в дуэлях: {count}"
profile_achievements = "Достижения {have}/{total}:"
profile_locked = "\nЕщё закрыты:"
ranks_empty = "Рейтинг пока пуст. Ловите объекты в «Бам» ⚔️"
ranks_title = "🏆 Рейтинг чата по BP:\n"
ranks_footer = "\nСвой профиль: /me"

# duel bets, /bet
bet_too_late = 'Ставки принимаются, только пока вызов не принят ⏳'
bet_by_duelist = 'Дуэлянтам ставить нельзя, это договорняк 😏'
bet_on_outsider = 'Этот человек не участвует в дуэли'
bet_too_small = 'Ставка должна быть хотя бы 1 BP'
bet_other_side = 'Ты уже поставил(а) на другого, переобуваться нельзя 👟'
bet_too_big = 'Не больше {max} BP на одну дуэль'
bet_no_money = 'Не хватает BP: у тебя {balance} BP'
bank_empty = '💰 Ставок пока нет. Кнопки ниже или /bet <сумма> @ник, до {max} BP'
bank_side = 'на {name} {amount}'
bank = '💰 Банк: {total} BP ({parts})'
bets_settled = '💰 Ставки:'

# duels, /duel
duel_topic = ' по теме {topic}'
duel_challenge = '⚔️ {challenger} вызывает {opponent} на дуэль{topic}!\n\nОдин вопрос на двоих. Кто ответит правильно и быстрее, забирает {prize} BP.\nУ {opponent} есть {minutes} минут, чтобы принять вызов.'
duel_title = '⚔️ Дуэль: {challenger} vs {opponent}'
duel_question = '⚔️ Дуэль: {challenger} vs {opponent}\n⏱ {seconds} секунд, отвечают только дуэлянты\n\n'
duel_no_answer = '😴 {name} не успел(а) ответить'
duel_answer = '{mark} {name}: {option} ({seconds} с)'
duel_winner = '🏆 Побеждает {winner}! +{prize} BP'
duel_draw = '🤝 Ничья, BP остаются при своих.'
duel_expired = "⌛ {opponent} так и не принял(а) вызов {challenger}. Струсил(а)?"

# IQ from the quiz, /show_iq; lowest IQ -> [title, emoji]
iq_levels = {
    0: ["Пускает слюни...", "🤤"],
    71: ["Обезьяна с гранатой", "🙊"],
    85: ["Homo Sapiens обыкновенный", "🙂"],
    116: ["Человек, которому черепушка жмёт :)", "🤓"],
    145: ["Мега мозг!", "🤯"],
    160: ["Кодзима нервно курит...", "🤩"],
    500: ["Boss of the GYM!!!", "😈"],
}
iq_row = "{prize}{name} имеет уровень интеллекта: {iq}. \n{title} -> {emoji}\n=============================\n"
iq_up = "Твой уровень IQ вырос с {old} до {new}!\n{name} умнеет!\nАй молодчинка :)"
iq_down = "Твой уровень IQ упал с {old} до {new}!\nОй-ой, {name} понемногу тупеет :(\nБудешь ням-ням димедрольчик?"
anti_cheat = (
    "Читер в чате!!!\n"
    "{name} хочет всех надурить и пытается ответить на вопрос, на который уже знает верный ответ!\n"
    "Вот как тебе не стыдно, GENIUS?"
)

# "Жиртрест дня", /fatstats
times_forms = ("раз", "раза", "раз")
fat_stats_empty = "Жиртрестов ещё не было. Исправим: /fat 🍩"
fat_stats_title = "🍔 Зал славы жиртрестов:\n"

# the loot under "Бам"
loot_first_takes = "Кто первый нажмёт, тот и заберёт: +{points} BP"

# /members
members_present = '👥 В чате ({count}):'
members_gone = '\n🚪 Ушли ({count}):'
members_footer = '\nКто ни разу не писал при боте, появится здесь после первого сообщения.'

# /party
party_title = '🎮 Собираем пати в MLBB!'
party_count = '\nВ деле {count}/{size}:'
party_gathered = '\n✅ Пати собрана!'
party_expired = '\n💨 Не собрались за {hours} часа. Новая пати: /party'
party_join_hint = '\nЖми «Я в деле» 👇'
party_call = ' — пати собрана, заходим в игру! 🎮'

# the quiz
question_forms = ("вопрос", "вопроса", "вопросов")
quiz_limit = "На сегодня всё: {limit} {questions} в день 🧠🔥\nМозгу нужен отдых, новые вопросы — завтра с 00:00 по Киеву."
quiz_pick_topic = "Какую тему хотите? 👇"
quiz_right_answer = "Правильный ответ: {answer}"
quiz_expired = "⏰ Время вышло, никто не ответил!"
answered_none = "Вот ленивая срака! Ещё ни на один вопрос не ответили ("
answered_title = "Вы уже ответили на следующие вопросы:\n"
leaders_title = "Лидеры в дисциплине {topic}, сезон {season}\nvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv\n"
leaders_row = "{name}: {count} верных ответов\n==============================\n"
all_leaders_title = "🏆 Лидеры викторины по темам, текущие сезоны"
all_leaders_topic = "\n{topic}, сезон {season}:"
all_leaders_empty = "\nПока без лидеров: {topics}"
all_leaders_footer = "\nСыграть: /quiz"
season_end = "🏁 Сезон {season} в дисциплине {topic} завершён! Вопросы закончились.\n"
season_winners = "Победители:\n"
season_no_winners = "Победителей нет, никто не ответил правильно (\n"
season_next = "\nНачинаем сезон {season}!"
disciplines_title = "Дисциплины викторины:\n"
disciplines_row = "{marker}{code}: {title} ({count} {questions})\n"
disciplines_footer = (
    "\nВопрос на любую тему: /quiz <тема>, например /quiz мобла"
    "\nСменить тему вопросов по расписанию (только админы чата): /discipline <тема>"
)

# "we miss you" roll call of the inactive
day_forms = ("день", "дня", "дней")
miss_you_title = "Внимание! Внимание!\nНаш бот разыскивает пропавших без вести!\n"
miss_you_row = "{name} @{username}, о тебе мы не слышали уже {days} {days_word} :(\n"
miss_you_footer = "Бот и весь чат скучают по вам...\nНапишите, как у вас дела.\nЖдём вас :)"

# the weekly summary, /week
message_forms = ("сообщение", "сообщения", "сообщений")
right_answer_forms = ("верный ответ", "верных ответа", "верных ответов")
week_title = "📅 Итоги недели {first} – {last}"
week_talkers = "💬 Болтуны недели:"
week_total = "Всего в чате: {count} {messages}"
week_brains = "🧠 Мозги недели:"
week_farmers = "⚔️ Фармеры недели:"
week_top_loot = ", Лордов: {count}"
week_fatties = "🍩 Жиртресты недели: {names}"
week_medals = "🏆 Новые медали:"
week_parties = "🎮 Собрано пати: {count}"
week_quote = "📜 Цитата недели"
week_silent = "🦗 Молчуны недели: {names}. Мы скучаем, напишите хоть что-нибудь!"
week_mvp = "👑 MVP недели: {name}!"
week_quiet = "Тихая неделя... Даже жиртреста никто не вычислил. Исправляйтесь: /fat /quiz /party 🙃"

# "Кто из нас…" poll results
vote_forms = ("голос", "голоса", "голосов")
who_no_votes = "🗳 «{question}»\n\nНикто не проголосовал 😴 Видимо, все сразу поняли, о ком речь."
who_result = "🗳 «{question}»\n\nПо мнению чата, это "
who_and = " и "
who_shared = ", делят титул поровну 🤝"

# quiz and other commands
chat_id = 'ID этого чата: {id}'
unknown_topic = 'Не знаю такой темы 🤔\n\n'
own_question_first = 'Сначала ответь на свой вопрос 👆'
discipline_admins_only = 'Менять дисциплину могут только админы чата 😈'
discipline_set = 'Теперь вопросы по расписанию на тему {topic}! Следующий вопрос: /quiz'

# duel and bet commands and buttons
duel_how_to = 'Кого вызываешь? Ответь /duel на сообщение соперника или напиши /duel @ник (можно с темой: /duel @ник мобла)'
duel_unknown_person = 'Не знаю такого человека в чате 🤔'
duel_self = 'Дуэль с самим собой? Это называется шизофрения 🙃'
duel_busy_you = 'У тебя уже есть незаконченная дуэль ⚔️'
duel_busy_opponent = 'У соперника уже есть незаконченная дуэль ⚔️'
duel_accept_button = '⚔️ Принять'
duel_decline_button = '🏳️ Отказаться'
bet_button = '💰 +{stake} на {name}'
duel_over = 'Эта дуэль уже закончилась'
bet_taken = 'Ставка принята! Всего {total} BP 💰'
bet_how_to = 'Ставки на дуэли: /bet <сумма> @ник, например /bet 20 @alex, до {max} BP.\nСтавить можно, пока вызов не принят. Или жми кнопки под вызовом 💰'
bet_no_duel = 'У {name} сейчас нет дуэли, на которую можно поставить 🤷'
bet_placed = '💰 {who} ставит {amount} BP на {name}!'
duel_stale = 'Вызов уже не актуален'
duel_cancelled = '🏳️ {name} отменил(а) вызов.'
duel_declined = '🏳️ {name} отказался(ась) от дуэли.'
bets_refunded = '\n💰 Ставки вернули.'
duel_not_you = 'Это не тебя вызвали 🍿'
duel_go = 'Поехали! ⚔️'
duel_watch_only = 'Ты не участвуешь в этой дуэли, просто смотри 🍿'
duel_already_answered = 'Ты уже ответил(а), ждём соперника ⏳'
duel_answer_taken = 'Ответ принят, ждём соперника ⏳'

# admin commands
group_only = 'Эта команда работает только в группе 👥'
members_admins_only = 'Проверять участников могут только админы чата 😈'

# party buttons
party_dead = 'Эта пати уже не работает, собери новую: /party'
party_join_button = '✅ Я в деле'
party_leave_button = '❌ Выхожу'
party_already_open = 'Пати уже собирается, жми кнопку тут 👆'
party_already_gathered = 'Пати уже собрана 🎮'
party_already_in = 'Ты уже в пати 😉'
party_joined = 'Ты в деле! 🎮'
party_not_in = 'Тебя и так нет в пати 🤷'
party_left = 'Ты вышел из пати'

# quiz buttons
topic_button_dead = 'Эта кнопка уже не работает, напишите /quiz'
topic_not_yours = 'Это не твой /quiz 😉 Вызови свой: /quiz'
topic_taken = 'Тему уже выбрали'
own_question_above = 'Сначала ответь на свой вопрос, он выше 👆'
question_closed = 'Этот вопрос уже закрыт'
question_not_yours = 'Ворюга! 😈 Это вопрос для {name}. Вызови свой: /quiz'

# quote book, /save and /quote
quote_book_empty = 'Цитатник пока пуст 📭\nОтветь командой /save на смешное сообщение, и оно попадёт сюда.'
save_how_to = 'Ответь командой /save на сообщение, которое надо увековечить 📜'
save_text_only = 'В цитатник попадает только текст 🤷'
unknown_author = 'Неизвестный гений'
quote_already_saved = 'Эта цитата уже в цитатнике 📜'
quote_saved = 'Сохранено в цитатник 📜 Всего цитат: {count}'
quote_none_of = 'У «{author}» цитат пока нет 🤔'
quote_of_the_day = '📜 Цитата дня'

# /who
who_already_open = 'Опрос уже идёт, голосуй тут 👆'
who_not_enough = 'Для опроса нужно хотя бы двое знакомых боту людей в чате 🤷'

# birthdays, /birthday and /birthdays
year_forms = ("год", "года", "лет")
birthday_how_to = (
    "Указать свой день рождения: /birthday 03.05 или с годом /birthday 03.05.1990\n"
    "Админ может указать за другого: ответить /birthday 03.05 на его сообщение. Забыть дату: /birthday -"
)
birthday_known = "🎂 День рождения {name}: {date}"
birthday_unknown = "🎂 Дня рождения пока не знаю."
birthday_saved = "🎂 Запомнил: {name} празднует {date}. Утром в этот день поздравим!"
birthday_forgotten = "🗑 Забыл день рождения {name}."
birthday_bad_date = "Не похоже на дату 🤔"
birthday_admins_only = "Указывать день рождения за других могут только админы чата 😈"
birthdays_empty = "Ни одного дня рождения пока не знаю 🤷\nУкажи свой: /birthday 03.05"
birthdays_title = "🎉 Ближайшие дни рождения:\n"
birthdays_today = "сегодня!"
birthdays_in = "через {days} {days_word}"
birthdays_footer = "\nДобавить свой: /birthday 03.05"
birthday_age = " — {age} {years}!"
birthday_openers = [
    "🎉 Внимание, чат! Сегодня день рождения!",
    "🥳 Бам! Сегодня у нас именинник!",
    "🎈 Отложите булочки, сегодня праздник!",
]
birthday_wishes = [
    "Поздравляем! Здоровья, денег, побед в каждой катке и чтобы жиртрестом дня тебя выбирали только по любви 🍩",
    "С днём рождения! Пусть IQ растёт, а вес — наоборот 🎂",
    "Поздравляем! Пусть баги обходят стороной, а торт будет большим 🎁",
    "С днём рождения! Желаем мифического ранга в жизни и легендарного дропа каждый день 🏆",
]

# gaming news, /news
news_title = "🎮 Игровые новости, {date}"
news_empty = "Свежих новостей пока нет, всё уже было 📰"
news_off = "Новости у этого бота выключены 📰"
