import csv
import json
import openai
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
    except:
        return {"suggested_action": "ACTION_NONE"}


if __name__ == "__main__":
    matched_action = 0
    expected_classified = 0
    tp, fp, tn, fn = 0, 0, 0, 0
    with open("eval/openai_eval_results.csv", "w") as eout:
        writer = csv.writer(eout)
        for i, line in enumerate(csv.reader(open("eval/openai_eval.csv", "r"))):
            user_content, expected_classification = line[0], line[1]
            if expected_classification != "NONE":
                expected_classification += 1

            openai_classification = (
                result["suggested_action"]
                if result["suggested_action"] == "ACTION_NONE"
                else (
                    result["subsubtype"]
                    if "subsubtype" in result.keys()
                    else result["subtype"]
                )
            )

            result = openai_eval(user_content)
            if openai_classification == "ACTION_NONE":
                if expected_classification == "NONE":
                    tn += 1
                else:
                    fn += 1
            else:
                if expected_classification == "NONE":
                    fp += 1
                else:
                    tp += 1
                    if openai_classification == expected_classification:
                        matched_action += 1

            mar = matched_action / expected_classified
            tpr = tp / expected_classified
            fnr = fn / expected_classified
            fpr = (
                (fp / (i + 1 - expected_classified))
                if (i + 1 - expected_classified) > 0
                else 0
            )
            tnr = (
                (tn / (i + 1 - expected_classified))
                if (i + 1 - expected_classified) > 0
                else 0
            )

            print(
                f"After example {i+1} EC={expected_classified} MA={mar} TP={tpr} FP={fpr} TN={tnr} FN={fnr}"
            )

            writer.writerow(
                [user_content, expected_classification, openai_classification]
            )
            eout.flush()
