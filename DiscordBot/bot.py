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
from enum import Enum, auto

class modState(Enum):
    MOD_REPORT_START = auto()
    MOD_REPORT_INACTIVE = auto()
    MOD_REPORT_INTIMATE_IMAGE = auto()
    MOD_REPORT_COERCIVE = auto()  
    MOD_REPORT_MINOR_VICTIM= auto()

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
        self.mod_state = modState.MOD_REPORT_INACTIVE
        self.reportMsgIDtoUserID = {}
        self.userIDtoNumMalReports = {}

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
            uid = self.reportMsgIDtoUserID[payload.message_id]
            if (uid not in self.userIDtoNumMalReports.keys()):
                self.userIDtoNumMalReports[uid] = 1
            else: 
                self.userIDtoNumMalReports[uid] += 1
            
            if (self.userIDtoNumMalReports[uid] == 1): 
                await self.mod_channels[payload.guild_id].send(f'A waring has been issued to the user with user ID : {uid} for malicious report')
            else:
                await self.mod_channels[payload.guild_id].send(f'The reporting feature has been suspended for user ID : {uid} for x amount of time.')            
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
            await self.do_mod_flow(mod_channel, self.reports[author_id], author_id)
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        mod_channel = self.mod_channels[message.guild.id]
        if self.mod_state == modState.MOD_REPORT_START and message.channel.name == f'group-{self.group_num}-mod':
            if message.content.lower() == 'yes':
                self.mod_state = modState.MOD_REPORT_INTIMATE_IMAGE
                await mod_channel.send('Is the imagery consensually taken or shared? Please respond with yes or no.')
                return
            if message.content.lower() == 'no':
                self.mod_state = modState.MOD_REPORT_COERCIVE
                await mod_channel.send('Does the content coercively request intimate or sexual content? Please respond with yes or no.')
                return
        if self.mod_state == modState.MOD_REPORT_INTIMATE_IMAGE and message.channel.name == f'group-{self.group_num}-mod':
            if message.content.lower() == 'yes':
                self.mod_state = modState.MOD_REPORT_INACTIVE
                await mod_channel.send('No action is taken and an explanation to reporter based on our criteria has been issued.')
                return
            if message.content.lower() == 'no':
                self.mod_state = modState.MOD_REPORT_INACTIVE
                await mod_channel.send('The perpetrator has been permanently banned. The user has been given the option to have their image(s) removed from the hash database.')
                return
        if self.mod_state == modState.MOD_REPORT_COERCIVE and message.channel.name == f'group-{self.group_num}-mod':
            if message.content.lower() == 'yes':
                self.mod_state = modState.MOD_REPORT_MINOR_VICTIM
                await mod_channel.send('Is the victim a minor? Please respond with yes or no.')
                return
            if message.content.lower() == 'no':
                self.mod_state = modState.MOD_REPORT_INACTIVE
                await mod_channel.send('No action is taken and an explanation to reporter based on our criteria has been issued.')
                return
        if self.mod_state == modState.MOD_REPORT_MINOR_VICTIM and message.channel.name == f'group-{self.group_num}-mod':
            if message.content.lower() == 'yes':
                self.mod_state = modState.MOD_REPORT_INACTIVE
                await mod_channel.send('The perpetrator has been permanently banned. The user has been given the option to have their image(s) removed from the hash database.')
                return
            if message.content.lower() == 'no':
                self.mod_state = modState.MOD_REPORT_INACTIVE
                await mod_channel.send('The perpetrator has been banned for 7-30 days')
                return
         
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
            await self.do_mod_flow(mod_channel, self.reports[author_id], author_id)
            self.reports.pop(author_id)

        
    async def do_mod_flow(self, mod_channel, report, author_id):
        # Forward the message to the mod channel
        if author_id in self.userIDtoNumMalReports.keys() and self.userIDtoNumMalReports[author_id] > 1:
            await mod_channel.send(f'User with uid : {author_id} has submitted a report however their reporting feature is suspended.')
            return
        fwd = await mod_channel.send(f'Forwarded message:\n{report.message.author.name}, (UID = {report.message.author.id}) : "{report.message.content}"')
        self.reportMsgIDtoUserID[fwd.id] = author_id 
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
        await mod_channel.send('Does the content include intimate imagery? Please respond with yes or no.')
        self.mod_state = modState.MOD_REPORT_START
        

    
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