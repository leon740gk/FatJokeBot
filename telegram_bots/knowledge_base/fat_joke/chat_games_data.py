# Chat games, see telegram_bots/engine/services/chat_games.py; an empty list turns a game off.
# FatJoke has none yet: the same lists as in knowledge_base/servo_skull/chat_games_data.py, in Russian, turn them on.

# "Это или то": (poll question, option, option)
this_or_that = []

# "Сегодня играю в…": open votes, several answers allowed, up to 10 options
tonight_question = "🎮 Сегодня играю в…"
tonight_options = []

# the question of the day, answered with a reply
daily_questions = []

# "Угадай игру": (clue, [hints from vague to obvious], [answers, the first one is shown at the end])
riddles = []
