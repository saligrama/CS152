from enum import Enum, auto
import discord
import re

class modState(Enum):
    MOD_REPORT_INACTIVE = auto()
    MOD_REPORT_START = auto()
    MOD_REPORT_IMMEDIATE_DANGER = auto()
    MOD_REPORT_ILLEGAL = auto()
    MOD_REPORT_CSAM = auto()
    MOD_REPORT_MALICIOUS = auto()
    MOD_REPORT_INTIMATE_IMAGE = auto()
    MOD_REPORT_CONSENSUAL = auto()
    MOD_REPORT_COERCIVE = auto()  
    MOD_REPORT_MINOR_VICTIM= auto()
    MOD_REPORT_OTHER_CATEGORIES = auto()

class review: 
    def __init__(self, modChannel, reportedMessage, reportingAuthorID):
        self.state = modState.MOD_REPORT_INACTIVE
        self.mod_channel = modChannel
        self.reported_message = reportedMessage
        self.reporting_author_id = reportingAuthorID
    
    def handle_emoji(message, emoji): 
        return 
    
    def handle_message(message): 
        return 


