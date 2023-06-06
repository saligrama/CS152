#!/usr/bin/env python3

import csv

if __name__ == "__main__":
    total = 0
    action_correct = 0
    expected_classified = 0
    tp, fp, tn, fn = 0, 0, 0, 0
    with open("eval/openai_eval_results_v2.csv", "r") as fin:
        for line in csv.reader(fin):
            total += 1
            _, expected, openai_res = line
            if expected != "ACTION_NONE":
                expected_classified += 1
                if openai_res != "ACTION_NONE":
                    tp += 1
                    if openai_res == expected:
                        action_correct += 1
                else:
                    fn += 1
            else:
                if openai_res == "ACTION_NONE":
                    tn += 1
                else:
                    fp += 1

    tpr = tp / expected_classified
    fnr = fn / expected_classified
    fpr = fp / (total - expected_classified)
    tnr = tn / (total - expected_classified)
    acc_with_action = action_correct / expected_classified
    acc_overall = (action_correct + tn) / total
    print(
        f"ACC_POS={acc_with_action} ACC_OVR={acc_overall} TP={tpr} FP={fpr} TN={tnr} FN={fnr}"
    )
