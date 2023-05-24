# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
import pdb

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
        

    async def on_raw_reaction_add(self, payload):
        print (payload)
        #only handles reactions in the mod channel
        if payload.channel_id != self.mod_channels[payload.guild_id].id:
            return
        #Igonres its own reactions
        if payload.member.id == self.user.id:
            return
        if payload.emoji.name == '1️⃣':
            await self.mod_channels[payload.guild_id].send('In response to your :one: reaction : law enforcement is contacted for imminant danger')
        if payload.emoji.name == '2️⃣':
            await self.mod_channels[payload.guild_id].send('In response to your :two: reaction : law enforcement is contacted for CSAM')
        if payload.emoji.name == '3️⃣':
            await self.mod_channels[payload.guild_id].send('In response to your :three: reaction : TODO:implement what to do for malicious report')
        if payload.emoji.name == '4️⃣':
            await self.mod_channels[payload.guild_id].send('In response to your :four: reaction : report escelated to higher level reviewers')
        
        
        
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
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
            await self.do_mod_flow(mod_channel, self.reports[author_id])
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
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
            #report is finished    
            mod_channel = self.mod_channels[message.guild.id]
            await self.do_mod_flow(mod_channel, self.reports[author_id])
            self.reports.pop(author_id)

        
    async def do_mod_flow(self, mod_channel, report):
        # Forward the message to the mod channel
        fwd = await mod_channel.send(f'Forwarded message:\n{report.message.author.name}, (UID = {report.message.author.id}) : "{report.message.content}"')

        await fwd.add_reaction('1️⃣')
        await fwd.add_reaction('2️⃣')
        await fwd.add_reaction('3️⃣')
        await fwd.add_reaction('4️⃣')

        context_strings = [f'{message.author.name} : "{message.content}" _({len(message.attachments)} attachments)_' for message in report.context]
        context_strings = '\n  '.join(context_strings)
        await mod_channel.send(f'Surrounding context:\n  {context_strings}')

        for a in report.message.attachments:
            await mod_channel.send(f'Has attachment with type "{a.content_type}" and description "{a.description}": ' + a.proxy_url)
        
        await mod_channel.send(f'Reported for: ({report.category}, {report.subcategory}, {report.subsubcategory})')        

        scores = self.eval_text(report.message.content)
        await mod_channel.send(self.code_format(scores))
        await mod_channel.send('React to the forwarded message based on the moderator flow below: ')
        await mod_channel.send('Is anyone in immediate danger? If yes React with : :one: ')
        await mod_channel.send('Does this contain CSAM? If yes React with: :two:')
        await mod_channel.send('Is this a malicious report? If yes react with: :three:')
        await mod_channel.send('Do you need to escalate it to a higher level reviewer? If yes react with: :four:')
        

    
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return message

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"


client = ModBot()
client.run(discord_token)