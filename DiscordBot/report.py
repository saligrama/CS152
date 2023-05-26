from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_CATEGORY = auto()
    AWAITING_SUBCATEGORY = auto()
    AWAITING_SUBSUBCATEGORY = auto()
    AWAITING_CONFIRMATION = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    EMOJI_CANCEL = "❌"

    CATEGORY_EMOJIS = {
        "spam": "1️⃣",
        "offensive content": "2️⃣",
        "harassment": "3️⃣",
        "imminent danger": "4️⃣",
    }

    SUBCATEGORY_EMOJIS = ["🇦", "🇧", "🇨", "🇩", "🇪"]
    SUBSUBCATEGORY_EMOJIS = ["⭐", "🌟", "💫", "✨", "🌠"]

    CATEGORIES = {
        "spam": ["spam1", "spam2", "spam3"],
        "offensive content": ["offensive1", "offensive2", "offensive3"],
        "harassment": ["harassment1", "harassment2", "harassment3"],
        "imminent danger": ["danger1", "danger2", "danger3"],
    }

    SUBCATEGORIES = {
        "spam1": ["subspam1a", "subspam1b"],
        "spam2": ["subspam2a", "subspam2b"],
        # ...
    }

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.context = None
        self.category = None
        self.subcategory = None
        self.subsubcategory = None

    async def handle_reaction(self, reaction, user):
        if reaction.message.author.id != self.client.user.id:
            return []

        if reaction.emoji == self.EMOJI_CANCEL:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]

        if self.state == State.AWAITING_CATEGORY:
            for category, emoji in self.CATEGORY_EMOJIS.items():
                if reaction.emoji == emoji:
                    self.category = category
                    self.state = State.AWAITING_SUBCATEGORY
                    return [
                        f"You've selected {self.category}. Please select the subcategory."
                    ]

        if self.state == State.AWAITING_SUBCATEGORY:
            for i, subcategory in enumerate(self.CATEGORIES[self.category]):
                if reaction.emoji == self.SUBCATEGORY_EMOJIS[i]:
                    self.subcategory = subcategory
                    self.state = State.AWAITING_SUBSUBCATEGORY
                    return [
                        f"You've selected {self.subcategory}. Please select the subsubcategory."
                    ]

        if self.state == State.AWAITING_SUBSUBCATEGORY:
            for i, subsubcategory in enumerate(self.SUBCATEGORIES[self.subcategory]):
                if reaction.emoji == self.SUBSUBCATEGORY_EMOJIS[i]:
                    self.subsubcategory = subsubcategory
                    self.state = State.AWAITING_CONFIRMATION
                    return [
                        f"You've selected {self.subsubcategory}. Please confirm your selection."
                    ]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.report = Report(self)

    async def on_ready(self):
        print(f'We have logged in as {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content == self.report.START_KEYWORD:
            await message.channel.send(
                "Thank you for starting the reporting process. "
                "Say `help` at any time for more information.\n\n"
                "Please copy paste the link to the message you want to report.\n"
                "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            )
            self.report.state = State.AWAITING_MESSAGE

        elif self.report.state == State.AWAITING_MESSAGE:
            m = re.search("/(\d+)/(\d+)/(\d+)", message.content)
            if not m:
                return [
                    "I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."
                ]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return [
                    "I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."
                ]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return [
                    "It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."
                ]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return [
                    "It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."
                ]
            self.message = message
            self.context = [
                message async for message in channel.history(around=message, limit=7)
            ]
            self.context.sort(key=lambda m: m.created_at)

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED

        elif self.report.state == State.MESSAGE_IDENTIFIED:
            reply_message = await message.channel.send(
                "Please specify the category of the issue by reacting to this message: "
                f"{', '.join(f'{emoji} for {category}' for category, emoji in self.report.CATEGORY_EMOJIS.items())}"
            )
            for emoji in self.report.CATEGORY_EMOJIS.values():
                await reply_message.add_reaction(emoji)
            self.report.state = State.AWAITING_CATEGORY

        elif self.report.state == State.AWAITING_CATEGORY:
            reply_message = await message.channel.send(
                "Please specify the subcategory of the issue by reacting to this message: "
                f"{', '.join(f'{emoji} for {subcategory}' for i, subcategory in enumerate(self.report.CATEGORIES[self.report.category]))}"
            )
            for emoji in self.report.SUBCATEGORY_EMOJIS[:len(self.report.CATEGORIES[self.report.category])]:
                await reply_message.add_reaction(emoji)
            self.report.state = State.AWAITING_SUBCATEGORY

        elif self.report.state == State.AWAITING_SUBCATEGORY:
            reply_message = await message.channel.send(
                "Please specify the subsubcategory of the issue by reacting to this message: "
                f"{', '.join(f'{emoji} for {subsubcategory}' for i, subsubcategory in enumerate(self.report.SUBCATEGORIES[self.report.subcategory]))}"
            )
            for emoji in self.report.SUBSUBCATEGORY_EMOJIS[:len(self.report.SUBCATEGORIES[self.report.subcategory])]:
                await reply_message.add_reaction(emoji)
            self.report.state = State.AWAITING_SUBSUBCATEGORY

    async def on_reaction_add(self, reaction, user):
        if user != self.user:
            responses = await self.report.handle_reaction(reaction, user)
            for response in responses:
                await reaction.message.channel.send(response)
            if self.report.report_complete():
                self.report = Report(self)  # reset the report

client = MyClient()