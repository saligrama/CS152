from dataclasses import dataclass
import json
from typing import Optional, Dict
from enum import Enum, auto
from textwrap import dedent
import discord
import openai
import requests
import cv2
import pdqhash
import numpy as np
from googleapiclient import discovery

perspective_client = {}
PDQ_BLACKLIST = [
    "90457290b72f220c6ad248565b23bbdccc698356bb63c97952cab4d769a6f963",  # img 1
    "ab1127cbf1a5329583cee5ca3cc44663b0f3a87903c095e33d8d9eae665e525a",  # img 2
    #"c32d343e4ed6705e2ecaec36db17724926566d8d9c1fe30d0f2e532191cb85d0",  # img 3
]
PDQ_HASH_LENGTH = 256

PDQ_BLACKLIST = [
    np.unpackbits(np.frombuffer(bytes.fromhex(s), dtype=np.uint8))
    for s in PDQ_BLACKLIST
]

OPENAI_PROMPT = open("prompts/moderator.txt", "r").read()
OPENAI_EXAMPLES_GENERIC = [
    {"role": "assistant", "content": json.dumps(d["content"])}
    if d["role"] == "assistant"
    else d
    for d in json.load(open("prompts/generic.json", "r"))
]
OPENAI_EXAMPLES_SEXTORTION = [
    {"role": "assistant", "content": json.dumps(d["content"])}
    if d["role"] == "assistant"
    else d
    for d in json.load(open("prompts/sextortion.json", "r"))
]


class OpenaiAction(Enum):
    ACTION_FLAG_DELETE = auto()
    ACTION_FLAG_DELETE_SUSPEND = auto()
    ACTION_DELETE = auto()
    ACTION_FLAG = auto()
    ACTION_NONE = auto()

    def __str__(self):
        pre = self.name.lower().split("_")[1:]
        return " and ".join(pre)


@dataclass
class EvaluationResult:
    openai_result: Dict[str, str]
    pdq_max_similarity: float
    perspective_results: Dict[str, float]

    def pretty_print(self) -> str:
        return dedent(
            f"""\
            **OpenAI suggested action**: {self.openai_result["suggested_action"]}

            **Perspective detected issues **: {[f'{category} (score: {score: .3f})' for category, score in self.perspective_results.items()]}

            **PDQ max similarity (known NCII)**: {self.pdq_max_similarity}\
            """
        )


def eval_all(message: discord.Message) -> EvaluationResult:
    return EvaluationResult(
        openai_result=openai_eval(message.content),
        pdq_max_similarity=pdq_eval_max_similarity(message),
        perspective_results=perspective_eval(message.content),
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


def perspective_eval(text: str) -> Dict[str, float]:
    detection = False
    detected_cats: Dict[str, float] = {}
    reqatts = {"SEVERE_TOXICITY": {}, "THREAT": {}, "IDENTITY_ATTACK": {}}
    analyze_request = {"comment": {"text": text}, "requestedAttributes": reqatts}

    response = perspective_client.comments().analyze(body=analyze_request).execute()
    for category in reqatts.keys():
        if response["attributeScores"][category]["summaryScore"]["value"] > 0.5:
            detected_cats[category] = response["attributeScores"][category][
                "summaryScore"
            ]["value"]

    return detected_cats


def openai_eval(text: str) -> Dict[str, str]:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": OPENAI_PROMPT},
                *OPENAI_EXAMPLES_GENERIC,
                *OPENAI_EXAMPLES_SEXTORTION,
                {"role": "user", "content": text},
            ],
        )

        gpt_classification = json.loads(response["choices"][0]["message"]["content"])
        gpt_classification["suggested_action"] = OpenaiAction[
            gpt_classification["suggested_action"]
        ]

        for cls_type in ["type", "subtype", "subsubtype"]:
            if cls_type in gpt_classification.keys():
                gpt_classification[cls_type] = " ".join(
                    gpt_classification[cls_type].lower().split("_")[1:]
                )

        return gpt_classification
    except:
        return {"suggested_action": OpenaiAction.ACTION_NONE}
