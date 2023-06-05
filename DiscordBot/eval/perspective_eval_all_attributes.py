from googleapiclient import discovery
import json
import os
import csv

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

analyze_request = {
  'comment': { 'text': '' },
  'requestedAttributes': {'SEVERE_TOXICITY': {}, 'THREAT':{}, 'TOXICITY': {}, 'IDENTITY_ATTACK':{}, 'PROFANITY':{}, 'INSULT':{}}
}

abusive_perspective_abusive = 0 #the number of abusive cases in the dataset that perspective detects
nonabusive_perspective_abusive = 0 # the number of non abusive cases in the dataset that perspective detects as abusive
abusive_perspective_nonabusive = 0 # the number of abusive cases that perspective detects as non abusive 
abusive_perspective_nonabusive = 0 # the number of non abusive cases that perspective detects as non abusive 
for i, line in enumerate(csv.reader(open("eval.csv", "r"))):
   user_content, expected_classification = line[0], line[1]
   analyze_request['comment']['text'] = user_content
   


response = client.comments().analyze(body=analyze_request).execute()
print(json.dumps(response, indent=2))