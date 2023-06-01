from enum import Enum, auto
import discord
import re
import evaluator

from report import Report
from malicious_reports import MaliciousReports


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


class Review:
    def __init__(
        self,
        mod_channel: discord.TextChannel,
        reporting_message: discord.Message,
        report: Report,
        malicious_reports: MaliciousReports,
        banned_users
    ):
        self.state = ModState.MOD_REPORT_INACTIVE
        self.reporting_message = reporting_message
        self.reporting_author = reporting_message.author

        self.mod_channel = mod_channel
        self.reported_channel = report.message.channel

        self.report = report
        self.malicious_reports = malicious_reports

        self.banned_users = banned_users

        self.began = False

    def handle_emoji(message: discord.Message, emoji):
        return

    def is_done(self):
        return self.began and self.state == ModState.MOD_REPORT_INACTIVE

    async def handle_raw_reaction(self, payload: discord.RawReactionActionEvent):
        if payload.emoji.name == "⏫":
            await self.mod_channel.send(
                "Report escalated to higher level reviewers due to ⏫ reaction."
            )

    async def begin_mod_flow(self):
        self.began = True
        # Forward the message to the mod channel
        if (
            self.reporting_author.id
            in self.malicious_reports.userIDtoNumMalReports.keys()
            and self.malicious_reports.userIDtoNumMalReports[self.reporting_author.id]
            > 1
        ):
            await self.reported_channel.send(
                f"User {self.reporting_author.name}, your reporting feature has been suspended."
            )
            await self.mod_channel.send(
                f"User with uid: {self.reporting_author.id} ({self.reporting_author.name}) has submitted a report, but their reporting feature is suspended due to a history of malicious reports."
            )
            return
        
        fwd = await self.mod_channel.send(
            f'Forwarded message:\n{self.report.message.author.name}, (UID = {self.report.message.author.id}) : "{self.report.message.content}"'
        )
        self.malicious_reports.reportMsgIDtoUserID[fwd.id] = self.reporting_author.id
        await fwd.add_reaction("⏫")

        context_strings = [
            f'{message.author.name} : "{message.content}" _({len(message.attachments)} attachments)_'
            for message in self.report.context
        ]
        context_strings = "\n  ".join(context_strings)
        await self.mod_channel.send(f"Surrounding context:\n  {context_strings}")

        for a in self.report.message.attachments:
            await self.mod_channel.send(
                f'Has attachment with type "{a.content_type}" and description "{a.description}": '
                + a.proxy_url
            )

        await self.mod_channel.send(
            f"Reported for: ({self.report.category}, {self.report.subcategory}, {self.report.subsubcategory})"
        )

        scores = evaluator.eval_all(self.report.message)
        await self.mod_channel.send(scores.prettyprint())

        await self.mod_channel.send(
            "At any point during the report handling process, please react with ⏫ to the forwarded message to escalate to higher level reviewers in case of ambiguity."
        )
        await self.mod_channel.send(
            "Is anyone in immediate danger? Please respond with yes or no."
        )
        self.state = ModState.MOD_REPORT_START

    async def handle_message(self, message: discord.Message):
        if self.state == ModState.MOD_REPORT_START:
            if message.content.lower() == "yes":
                self.state = ModState.MOD_REPORT_INACTIVE
                await self.mod_channel.send("Report has been sent to law enforcement.")
                return
            if message.content.lower() == "no":
                self.state = ModState.MOD_REPORT_ILLEGAL
                await self.mod_channel.send(
                    "Is there any evidence of illegal financial transactions? Please respond with yes or no."
                )
                return
        if self.state == ModState.MOD_REPORT_ILLEGAL:
            if message.content.lower() == "yes":
                self.state = ModState.MOD_REPORT_INACTIVE
                await self.mod_channel.send("Report has been sent to law enforcement.")
                return
            if message.content.lower() == "no":
                self.state = ModState.MOD_REPORT_CSAM
                await self.mod_channel.send(
                    "Does this contain CSAM? Please respond with yes or no."
                )
                return
        if self.state == ModState.MOD_REPORT_CSAM:
            if message.content.lower() == "yes":
                self.state = ModState.MOD_REPORT_INACTIVE
                await self.mod_channel.send(
                    "Report is sent to NCMEC and the reported account is permanently banned"
                )
                await self.report.message.delete()
                self.banned_users.add(self.report.message.author.id)
                return
            if message.content.lower() == "no":
                self.state = ModState.MOD_REPORT_MALICIOUS
                await self.mod_channel.send(
                    "Is this a malicious report? Please respond with yes or no."
                )
                return
        if self.state == ModState.MOD_REPORT_MALICIOUS:
            if message.content.lower() == "yes":
                self.state = ModState.MOD_REPORT_INACTIVE
                uid = message.author.id
                if uid not in self.malicious_reports.userIDtoNumMalReports.keys():
                    self.malicious_reports.userIDtoNumMalReports[uid] = 1
                else:
                    self.malicious_reports.userIDtoNumMalReports[uid] += 1

                if self.malicious_reports.userIDtoNumMalReports[uid] == 1:
                    await self.mod_channel.send(
                        f"A warning has been issued to the user with user ID : {uid} for malicious report"
                    )
                    await self.reported_channel.send(
                        f"User {self.reporting_author.name}: WARNING: Upon review of your report, we found that your report was made maliciously. If you continue to abuse the reporting feature this way, we will suspend your ability to report messages for 7 days upon your next infraction."
                    )
                else:
                    await self.mod_channel.send(
                        f"The reporting feature has been suspended for user ID : {uid} for 7 days."
                    )
                    await self.reported_channel.send(
                        f"User {self.reporting_author.name}: Your ability to report messages has been suspended for 7 days."
                    )
                return
            if message.content.lower() == "no":
                self.state = ModState.MOD_REPORT_INTIMATE_IMAGE
                await self.mod_channel.send(
                    "Does the content include intimate imagery? Please respond with yes or no."
                )
                return
        if self.state == ModState.MOD_REPORT_INTIMATE_IMAGE:
            if message.content.lower() == "yes":
                self.state = ModState.MOD_REPORT_CONSENSUAL
                await self.mod_channel.send(
                    "Is the imagery consensually taken or shared? Please respond with yes or no"
                )
                return
            if message.content.lower() == "no":
                self.state = ModState.MOD_REPORT_COERCIVE
                await self.mod_channel.send(
                    "Does the content coercively request intimate or sexual content? Please respond with yes or no."
                )
                return
        if self.state == ModState.MOD_REPORT_COERCIVE:
            if message.content.lower() == "yes":
                self.state = ModState.MOD_REPORT_MINOR_VICTIM
                await self.mod_channel.send(
                    "Is the victim a minor? Please respond with yes or no"
                )
                return
            if message.content.lower() == "no":
                self.state = ModState.MOD_REPORT_OTHER_CATEGORIES
                await self.mod_channel.send(
                    "Does this post fall under any of our other categories of concern? (eg. spam, hate speech, bullying)? Please respond with yes or no."
                )
                return
        if self.state == ModState.MOD_REPORT_MINOR_VICTIM:
            if message.content.lower() == "yes":
                self.state = ModState.MOD_REPORT_INACTIVE
                await self.mod_channel.send(
                    "The perpetrator has been warned and permanently banned."
                )
                await self.report.message.delete()
                self.banned_users.add(self.report.message.author.id)
                return
            if message.content.lower() == "no":
                self.state = ModState.MOD_REPORT_INACTIVE
                await self.mod_channel.send(
                    "The perpetrator has been warned and banned for 7 days."
                )
                await self.report.message.delete()
                self.banned_users.add(self.report.message.author.id)
                return
        if self.state == ModState.MOD_REPORT_OTHER_CATEGORIES:
            if message.content.lower() == "yes":
                self.state = ModState.MOD_REPORT_OTHER_CATEGORIES_ACTION_OUTCOMES
                await self.mod_channel.send(
                    "Select action outcome based on the severity of the reported content. Please respond with medium or high."
                )
                return
            if message.content.lower() == "no":
                self.state = ModState.MOD_REPORT_INACTIVE
                await self.mod_channel.send(
                    "An explanation for no action has been issued to the reporter based on our criteria."
                )
                return
        if self.state == ModState.MOD_REPORT_OTHER_CATEGORIES_ACTION_OUTCOMES:
            if message.content.lower() == "medium":
                self.state = ModState.MOD_REPORT_INACTIVE
                await self.mod_channel.send(
                    "The perpetrator has been warned, and their account has been banned for 7 days."
                )
                await self.report.message.delete()
                self.banned_users.add(self.report.message.author.id)
                return
            if message.content.lower() == "high":
                self.state = ModState.MOD_REPORT_INACTIVE
                await self.mod_channel.send(
                    "The perpetrator has been warned, and their account has been banned permanently."
                )
                await self.report.message.delete()
                self.banned_users.add(self.report.message.author.id)
                return
        if self.state == ModState.MOD_REPORT_CONSENSUAL:
            if message.content.lower() == "yes":
                self.state = ModState.MOD_REPORT_INACTIVE
                await self.mod_channel.send(
                    "An explanation for no action has been issued to the reporter based on our criteria."
                )
                return
            if message.content.lower() == "no":
                self.state = ModState.MOD_REPORT_INACTIVE
                await self.mod_channel.send(
                    "The perpetrator has been warned on the basis of violating our content policy and permanently banned. The user has been given the option to have the image(s) added to the hash database."
                )
                await self.report.message.delete()
                self.banned_users.add(self.report.message.author.id)
                return
