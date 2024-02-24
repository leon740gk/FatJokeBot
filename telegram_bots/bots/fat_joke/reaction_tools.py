import random


class Reactions:
    def __init__(self, bot, message):
        self.bot = bot
        self.message = message


class CommandHandler(Reactions):
    def text_to_command(self, phrase):
        self.bot.send_message(self.message.chat.id, text=phrase)


class ToTextReactions(Reactions):

    def _text_to_text_reply(self, mapper):
        something_to_say = [
            mapper.get(keywords)
            for keywords in mapper.keys()
            for i in keywords
            if i.lower() in self.message.text.lower()
        ]

        for phrase in something_to_say:
            if isinstance(phrase, str):
                self.bot.send_message(self.message.chat.id, text=phrase)
            elif isinstance(phrase, list):
                self.bot.send_message(self.message.chat.id, text=random.choice(phrase))

    def _text_to_text_reply_re(self, mapper):
        something_to_say = [mapper.get(regex) for regex in mapper.keys() if regex.findall(self.message.text.lower())]

        for phrase in something_to_say:
            self.bot.send_message(self.message.chat.id, text=phrase)

    def _sticker_to_text_reply(self, mapper):
        something_to_say = [
            mapper.get(keywords)
            for keywords in mapper.keys()
            for i in keywords
            if i.lower() in self.message.text.lower()
        ]

        for sticker in something_to_say:
            if isinstance(sticker, str):
                self.bot.send_sticker(self.message.chat.id, sticker=sticker)
            elif isinstance(sticker, list):
                self.bot.send_sticker(self.message.chat.id, sticker=random.choice(sticker))

    def _photo_to_text_reply(self, mapper):
        something_to_say = [
            mapper.get(keywords)
            for keywords in mapper.keys()
            for i in keywords
            if i.lower() in self.message.text.lower()
        ]

        for photo in something_to_say:
            if isinstance(photo, str):
                self.bot.send_photo(self.message.chat.id, photo=photo)
            elif isinstance(photo, list):
                self.bot.send_photo(self.message.chat.id, photo=random.choice(photo))

    def _bots_philosophy(self, bot_philosophy):
        frequency = 10
        say_something = random.randint(0, frequency)
        if say_something == frequency:
            random_wisdom = random.choice(bot_philosophy)
            self.bot.send_message(self.message.chat.id, text=random_wisdom)
        else:
            pass


class ToPhotoReactions(Reactions):

    def _react_to_photo(self, sticker):
        self.bot.send_sticker(self.message.chat.id, sticker=sticker)


class ToStickerReactions(Reactions):

    def _react_to_sticker(self, sticker_responses, special_responses: dict = None):
        something_to_say = None
        if special_responses:
            something_to_say = [
                random.choice(special_responses.get(keyword))
                for keyword in special_responses.keys()
                if keyword == self.message.sticker.file_unique_id
            ]
            for phrase in something_to_say:
                self.bot.send_message(self.message.chat.id, text=phrase)
        if not something_to_say:
            self.bot.send_message(self.message.chat.id, text=random.choice(sticker_responses))


class ToUserIdReactions(Reactions):
    def _react_to_user(self, person_name: str, user_ids: dict, person_reaction_mapper: dict, frequency: int = 1):
        if self.message.from_user.id == user_ids.get(person_name):
            shout_out = random.randint(0, frequency)
            if shout_out == frequency:
                self.bot.send_sticker(self.message.chat.id, sticker=person_reaction_mapper.get(person_name))
