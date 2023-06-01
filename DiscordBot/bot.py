# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from review import Review
from malicious_reports import MaliciousReports
import pdb
from enum import Enum, auto
import openai


class ModState(Enum):
    MOD_REPORT_INACTIVE = auto()
    MOD_REPORT_START = auto()
    MOD_REPORT_ILLEGAL = auto()
    MOD_REPORT_CSAM = auto()
    MOD_REPORT_MALICIOUS = auto()
    MOD_REPORT_INTIMATE_IMAGE = auto()
    MOD_REPORT_CONSENSUAL = auto()
    MOD_REPORT_COERCIVE = auto()
    MOD_REPORT_MINOR_VICTIM = auto()
    MOD_REPORT_OTHER_CATEGORIES = auto()
    MOD_REPORT_OTHER_CATEGORIES_ACTION_OUTCOMES = auto()


# Set up logging to the console
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = "tokens.json"
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens["discord"]
    openai.organization = tokens["openai"]["organization"]
    openai.api_key = tokens["openai"]["api_key"]


class ModBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        super().__init__(command_prefix=".", intents=intents)
        self.group_num = None
        self.mod_channels = {}  # Map from guild to the mod channel id for that guild
        self.reports = {}  # Map from user IDs to the state of their report
        self.reviews = {}  # Map from message IDs to the state of their report
        self.banned_users = set()  # Set of banned user IDs
        self.mod_state = ModState.MOD_REPORT_INACTIVE
        self.malicious_reports = MaliciousReports()

    async def on_ready(self):
        print(f"{self.user.name} has connected to Discord! It is these guilds:")
        for guild in self.guilds:
            print(f" - {guild.name}")
        print("Press Ctrl-C to quit.")

        # Parse the group number out of the bot's name
        match = re.search("[gG]roup (\d+) [bB]ot", self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception(
                'Group number not found in bot\'s name. Name format should be "Group # Bot".'
            )

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f"group-{self.group_num}-mod":
                    self.mod_channels[guild.id] = channel

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # only handles reactions in the mod channel that are not its own
        if (
            payload.channel_id == self.mod_channels[payload.guild_id].id
            and payload.member.id != self.user.id
        ):
            # hacky, TODO
            await next(iter(self.reviews.values())).handle_raw_reaction(payload)

    async def on_message(self, message: discord.Message):
        """
        This function is called whenever a message is sent in a channel that the bot can see (including DMs).
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel.
        """
        # Ignore messages from the bot
        if message.author.id == self.user.id:
            return


        if not message.guild: 
            return
        # the automatic detection pipeline function to be implemented
        await self.handle_automatic_detection(message)
        
        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)
    async def handle_automatic_detection(self, message:discord.Message): 
        if self.openai_eval(message.content) == "Threatening":
            mod_channel = self.mod_channels[message.guild.id]
            rp = Report(self)
            rp.state = rp.report_complete
            rp.category = "imminant danger"
            rp.subcategory = "threats"
            rp.message = message
            rp.context = [
                message async for message in message.channel.history(around=message, limit=7)
            ]
            rp.context.sort(key=lambda m: m.created_at)
            await self.do_mod_flow(
                mod_channel, rp, self.user.id, message
            )

    async def handle_user_message(self, message: discord.Message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply = "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return
        

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(
            Report.START_KEYWORD
        ):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            mod_channel = self.mod_channels[self.reports[author_id].message.guild.id]
            await self.do_mod_flow(
                mod_channel, self.reports[author_id], author_id, message
            )
            self.reports.pop(author_id)

    async def handle_dm(self, message: discord.Message):
        await self.handle_user_message(message)

    async def handle_channel_message(self, message: discord.Message):
        mod_channel = self.mod_channels[message.guild.id]

        # Only handle messages sent in the "group-#" channel
        if message.channel.name == f"group-{self.group_num}":
            # bans
            if message.author.id in self.banned_users: 
                await message.delete()
                await message.channel.send("_Message from banned user has been deleted._")
            else:
                await self.handle_user_message(message)
        elif message.channel.name == f"group-{self.group_num}-mod":
            await next(iter(self.reviews.values())).handle_message(message)

        # temporary abstraction: only one report at a time
        if len(self.reviews) > 0:
            key = next(iter(self.reviews))
            if self.reviews[key].is_done():
                del self.reviews[key]

    async def do_mod_flow(
        self,
        mod_channel: discord.TextChannel,
        report: Report,
        author_id: int,
        message: discord.Message,
    ):
        self.reviews[message.id] = Review(
            mod_channel, message, report, self.malicious_reports, self.banned_users
        )
        await self.reviews[message.id].begin_mod_flow()

    def eval_text(self, message):
        """'
        TODO: Once you know how you want to evaluate messages in your channel,
        insert your code here! This will primarily be used in Milestone 3.
        """
        return message

    def code_format(self, text):
        """'
        TODO: Once you know how you want to show that a message has been
        evaluated, insert your code here for formatting the string to be
        shown in the mod channel.
        """
        return "Evaluated: '" + text + "'"
    
    def openai_eval(self, text): 
        response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
        {"role": "system", "content": "You are a content moderation system. Classify each input as either threatening or not-threatening."},
        {"role": "user", "content": "I am going to kill you."},
        {"role": "assistant", "content": "Threatening"},
        {"role": "user", "content": "I love you"},
        {"role": "assistant", "content": "Not-threatening"},
        {"role": "user", "content": "You should kill yourself"},
        {"role": "assistant", "content": "Threatening"},
        {"role": "user", "content": text},

        ]
        )
        output = response['choices'][0]['message']['content']

        return output


client = ModBot()
client.run(discord_token)
