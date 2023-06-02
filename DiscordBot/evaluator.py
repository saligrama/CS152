from dataclasses import dataclass
from typing import Optional
from enum import Enum, auto
import discord
import openai
import requests
import cv2
import pdqhash
import numpy as np

PDQ_BLACKLIST = [
    "1cc64275f58c5f73899362bc55cf98bce30236dd89a6701bdfe4809e63631c07",
    "29aca96524d34ca69929cdb654cac555af6c2db5552aaaab275418d29ab7b5ac",
    "4993e8dfa0d9f5d8dcc6c816001a3216b6579c73dcf3dab18a912a343636b6ad",
    "7cf903cf7187e60ccc7c671c019f6ffffa79871f007708017201b238cfe20f06",
    "18c6bd8ab58ca08c89939d4355cf6743e302c9a289a68fe4dfc47f616363e3f8",
    "4d931720e0d90a27dcd637e9009acde9b657638cdcf3254e8ab1d5cb36366952",
    "29ac769a24d2b3599929b24954ca3aaaaf6cd24a552a5d542754e76d9ab75a53",
    "7cf9dc30718719f3cc7c18e3019f9000f83978e00077f7fe72014d87cfe2e0f9",
]
PDQ_HASH_LENGTH = 256

PDQ_BLACKLIST = [
    np.unpackbits(np.frombuffer(bytes.fromhex(s), dtype=np.uint8))
    for s in PDQ_BLACKLIST
]


class OpenaiAction(Enum):
    ACTION_FLAG_DELETE = auto()
    ACTION_FLAG_DELETE_SUSPEND = auto()
    ACTION_DELETE = auto()
    ACTION_FLAG = auto()
    ACTION_NONE = auto()


@dataclass
class EvaluationResult:
    openai_suggested_action: OpenaiAction
    pdq_max_similarity: float

    def pretty_print(self) -> str:
        return f"""OpenAI suggested action: {self.openai_suggested_action}
        
        PDQ max similarity (known NCII): {self.pdq_max_similarity}"""


def eval_all(message: discord.Message) -> EvaluationResult:
    return EvaluationResult(
        openai_suggested_action=openai_eval_threatening(message.content),
        pdq_max_similarity=pdq_eval_max_similarity(message),
    )


def pdq_singlehash_min_dist(hash) -> int:
    mindist = PDQ_HASH_LENGTH + 1
    for badhash in PDQ_BLACKLIST:
        # PDQ is hamming distance based
        mindist = min(mindist, (badhash != hash).sum())
    return mindist


# recall: PDQ https://drive.google.com/file/d/11L8bXR5-PWvJGBELGQTzONArhNi2HNUx/view
def pdq_eval_max_similarity(message: discord.Message) -> Optional[float]:
    max_sim = 0
    for attach in message.attachments:
        # for now only images supported
        if attach.content_type is not None and attach.content_type.startswith("image"):
            req = requests.get(attach.proxy_url)
            arr = np.asarray(bytearray(req.content), dtype=np.uint8)
            image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Get all the rotations and flips in one pass.
            # hash_vectors is a list of vectors in the following order
            # - Original
            # - Rotated 90 degrees
            # - Rotated 180 degrees
            # - Rotated 270 degrees
            # - Flipped vertically
            # - Flipped horizontally
            # - Rotated 90 degrees and flipped vertically
            # - Rotated 90 degrees and flipped horizontally
            hash_vectors, _ = pdqhash.compute_dihedral(image)
            max_sim = max(
                max_sim,
                *(
                    (PDQ_HASH_LENGTH - pdq_singlehash_min_dist(h)) / PDQ_HASH_LENGTH
                    for h in hash_vectors
                ),
            )
            # print(hash_vectors)
            # print(max_sim)
            # print(quality)
    return max_sim


def openai_eval_threatening(text: str) -> OpenaiAction:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": """You are a content moderation system. You will be given a message that should be evaluated based on how harmful it is to a user that sees it. Your suggestions will be used to potentially delete the message, suspend or ban the message's author, or pass the message along to a human for further review.

                When given a message, please respond with exactly one of the following responses and no other text:

                `ACTION_FLAG_DELETE`, which suggests that the message should be automatically deleted and also sent to a human for further review. The categories of message you should respond with `ACTION_FLAG_DELETE` are: “Violence and Gore”, “Coercing Sexual Favors or Content”, “Solicitation”, “Unwanted Sexual Content”, “Hate Speech”.

                `ACTION_FLAG_DELETE_SUSPEND`, which suggests that the message should be automatically deleted, its author be suspended, and also sent to a human for further review. The categories of message you should respond with `ACTION_FLAG_DELETE` are:  “Threatening Violence”, “Threats to Share Intimate Imagery”, “Self Harm and Suicide”, “Non-Consensual Intimate Imagery”, “Child Sex Abuse Content”, “Sexual Harassment”, “Publicizing Private Information”, “Sexual Harassment”, “Publicizing Private Information”, “Glorifying Violence”.

                `ACTION_DELETE`, which suggests that the message should be automatically deleted, but it won't be flagged for human review. The categories of message you should respond with `ACTION_DELETE` are: “Fraud”, “Impersonation”.

                `ACTION_FLAG`, which suggests that the message should be sent to a human review. Use this option if you are unsure about what action to take on the message.

                `ACTION_NONE`, which suggests that the message is not in violation of any conduct guidelines.

                Here are some examples of suggested responses. If you don't think a message fits into one of the categories provided above (i.e., it doesn't look anything like the examples provided below), respond by default with `ACTION_NONE`.""",
            },
            {"role": "user", "content": "Can you send me a topless photo?"},
            {"role": "assistant", "content": "ACTION_FLAG_DELETE"},
            {
                "role": "user",
                "content": "If I give you an address, will you go to there and steal something for me?",
            },
            {"role": "assistant", "content": "ACTION_FLAG_DELETE"},
            {"role": "user", "content": "I'm going to kill you"},
            {"role": "assistant", "content": "ACTION_FLAG_DELETE_SUSPEND"},
            {
                "role": "user",
                "content": "I have that nude photo of you and I'm going to post it for the world to see",
            },
            {"role": "assistant", "content": "ACTION_FLAG_DELETE_SUSPEND"},
            {
                "role": "user",
                "content": "I have nobody left to turn to and I'm going to slit my wrists",
            },
            {"role": "assistant", "content": "ACTION_FLAG_DELETE_SUSPEND"},
            {
                "role": "user",
                "content": "Melissa's social security number is 178-45-5967",
            },
            {"role": "assistant", "content": "ACTION_FLAG_DELETE_SUSPEND"},
            {
                "role": "user",
                "content": "I really love watching people get physically abused",
            },
            {"role": "assistant", "content": "ACTION_FLAG_DELETE_SUSPEND"},
            {
                "role": "user",
                "content": "Send $3,000 to this account and get tickets to meet Beyonce!",
            },
            {"role": "assistant", "content": "ACTION_DELETE"},
            {
                "role": "user",
                "content": "This is Elon Musk! Congratulations! You just won a Tesla Model X!",
            },
            {"role": "assistant", "content": "ACTION_DELETE"},
            {
                "role": "user",
                "content": "You're a loser!",
            },
            {"role": "assistant", "content": "ACTION_DELETE"},
            {"role": "user", "content": text},
        ],
    )

    try:
        return OpenaiAction[response["choices"][0]["message"]["content"]]
    except ValueError:
        return OpenaiAction.ACTION_NONE
