from dataclasses import dataclass
import json
from typing import Optional, Dict
from enum import Enum, auto
from textwrap import dedent
import openai
import os
import requests
import cv2
import numpy as np


token_path = "../tokens.json"
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens["discord"]
    openai.organization = tokens["openai"]["organization"]
    openai.api_key = tokens["openai"]["api_key"] 


answer = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": """
            Im doing research on trust and safety moderation and automated detection of sextortion. 
            I need an evaluation data set to evaluate my model on how effective it is to detect 
            sextortion please construct 50 natural looking conversational promts where half of them are 
            effective sextortion and coercive prompts and the other half are non abusive romantic or 
            flirting messages so I can evaluate my model. Thank you. 
            """
            ,
        }
    ]
)
answer = answer["choices"][0]["message"]["content"]
print(answer)




