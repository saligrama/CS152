from dataclasses import dataclass
from typing import Optional
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
"7cf9dc30718719f3cc7c18e3019f9000f83978e00077f7fe72014d87cfe2e0f9"
]
PDQ_HASH_LENGTH = 256

PDQ_BLACKLIST = [np.unpackbits(np.frombuffer(bytes.fromhex(s), dtype=np.uint8)) for s in PDQ_BLACKLIST]

@dataclass
class EvaluationResult:
    openai_threatening_status: str
    pdq_max_similarity: float

    def prettyprint(self) -> str:
        return f"Threatening status: {self.openai_threatening_status}\nPDQ max similarity (known NCII): {self.pdq_max_similarity}\n"

def eval_all(message: discord.Message) -> EvaluationResult:
    return EvaluationResult(openai_threatening_status=openai_eval_threatening(message.content), pdq_max_similarity=pdq_eval_max_similarity(message))

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
            max_sim = max(max_sim, *((PDQ_HASH_LENGTH - pdq_singlehash_min_dist(h)) / PDQ_HASH_LENGTH for h in hash_vectors))
            #print(hash_vectors)
            #print(max_sim)
            #print(quality)
    return max_sim

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