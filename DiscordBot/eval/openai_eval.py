import csv
import json
import openai
import backoff
from typing import Dict

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

with open("tokens.json", "r") as f:
    tokens = json.load(f)
    openai.organization = tokens["openai"]["organization"]
    openai.api_key = tokens["openai"]["api_key"]


@backoff.on_exception(backoff.expo, openai.error.RateLimitError)
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

        return json.loads(response["choices"][0]["message"]["content"])
    except ValueError as e:
        print(e)
        return {"suggested_action": "OPENAI_ERROR"}


if __name__ == "__main__":
    matched_action = 0
    expected_classified = 0
    evaluated = 0
    tp, fp, tn, fn = 0, 0, 0, 0
    with open("eval/openai_eval_results.csv", "w") as eout:
        writer = csv.writer(eout)
        for i, line in enumerate(csv.reader(open("eval/openai_eval_dataset.csv", "r"))):
            user_content, expected_classification = line[0], line[1]
            result = openai_eval(user_content)

            if result["suggested_action"] != "OPENAI_ERROR":
                if expected_classification != "ACTION_NONE":
                    expected_classified += 1
                    evaluated += 1

                openai_classification = (
                    result["suggested_action"]
                    if result["suggested_action"] == "ACTION_NONE"
                    else (
                        result["subsubtype"]
                        if "subsubtype" in result.keys()
                        else result["subtype"]
                    )
                )

                print(openai_classification)
                if openai_classification == "ACTION_NONE":
                    if expected_classification == "ACTION_NONE":
                        tn += 1
                    else:
                        fn += 1
                else:
                    if expected_classification == "ACTION_NONE":
                        fp += 1
                    else:
                        tp += 1
                        if openai_classification == expected_classification:
                            matched_action += 1

                mar = matched_action / expected_classified
                tpr = tp / expected_classified
                fnr = fn / expected_classified
                fpr = (fp / (i + 1 - evaluated)) if (i + 1 - evaluated) > 0 else 0
                tnr = (tn / (i + 1 - evaluated)) if (i + 1 - evaluated) > 0 else 0

                print(
                    f"After example {i+1} EC={expected_classified} MA={mar} TP={tpr} FP={fpr} TN={tnr} FN={fnr}"
                )

            writer.writerow(
                [user_content, expected_classification, openai_classification]
            )
            eout.flush()
