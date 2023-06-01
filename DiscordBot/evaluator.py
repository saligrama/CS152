from dataclasses import dataclass
import discord
import openai

@dataclass
class EvaluationResult:
    openai_threatening_status: str
    pdq_max_similarity: float

    def prettyprint(self) -> str:
        return f"Threatening status: {self.openai_threatening_status}\nPDQ max similarity (known NCII): {self.pdq_max_similarity}\n"

def eval_all(message: discord.Message) -> EvaluationResult:
    return EvaluationResult(openai_threatening_status=openai_eval_threatening(message.content), pdq_max_similarity=None)

def openai_eval_threatening(text): 
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