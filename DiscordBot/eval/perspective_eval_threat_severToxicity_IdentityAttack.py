from googleapiclient import discovery
import json
import os
import csv
import time

API_KEY = ""
token_path = "../tokens.json"
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    API_KEY = tokens["perspective"]


client = discovery.build(
  "commentanalyzer",
  "v1alpha1",
  developerKey=API_KEY,
  discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
  static_discovery=False,
)

reqatts =  {'SEVERE_TOXICITY': {}, 'THREAT':{}, 'IDENTITY_ATTACK':{}}

analyze_request = {
  'comment': { 'text': '' },
  'requestedAttributes': reqatts
}

abusive_perspective_abusive = 0 #the number of abusive cases in the dataset that perspective detects
nonabusive_perspective_abusive = 0 # the number of non abusive cases in the dataset that perspective detects as abusive
abusive_perspective_nonabusive = 0 # the number of abusive cases that perspective detects as non abusive 
abusive_perspective_nonabusive = 0 # the number of non abusive cases that perspective detects as non abusive 
for i, line in enumerate(csv.reader(open("eval.csv", "r"))):
   user_content, expected_classification = line[0], line[1]
   analyze_request['comment']['text'] = user_content

abusive_perspective_abusive = 0 #the number of abusive cases in the dataset that perspective detects
nonabusive_perspective_abusive = 0 # the number of non abusive cases in the dataset that perspective detects as abusive
abusive_perspective_nonabusive = 0 # the number of abusive cases that perspective detects as non abusive 
nonabusive_perspective_nonabusive = 0 # the number of non abusive cases that perspective detects as non abusive 
for i, line in enumerate(csv.reader(open("eval.csv", "r"))):
  user_content, expected_classification = line[0], line[1]
  analyze_request['comment']['text'] = user_content
  response = client.comments().analyze(body=analyze_request).execute()
  persAbs = False
  for x in reqatts.keys():
    if response["attributeScores"][x]["summaryScore"]["value"] > 0.5: 
      persAbs = True
  if (expected_classification != "ACTION_NONE"): 
    if persAbs: 
      abusive_perspective_abusive += 1
    if not persAbs: 
      abusive_perspective_nonabusive += 1 
  else:
    if persAbs:
      nonabusive_perspective_abusive += 1
    if not persAbs:
      nonabusive_perspective_nonabusive += 1
  time.sleep(1.1)
  print(i)
  print(persAbs)
  print(expected_classification)

print("abusive_perspective_abusive:")
print(abusive_perspective_abusive)

print("nonabusive_perspective_abusive:")
print(nonabusive_perspective_abusive)

print("abusive_perspective_nonabusive:")
print(abusive_perspective_nonabusive)

print("nonabusive_perspective_nonabusive:")
print(nonabusive_perspective_nonabusive)
