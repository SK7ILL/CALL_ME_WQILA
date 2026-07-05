from llm_sdk import Small_LLM_Model
import json

loaded = []
try:
    with open("data/input/functions_definition.json", "r") as file:
        loaded = json.load(file)
except BaseException as e:
    print(e)
s = Small_LLM_Model()

tn = []
for x in loaded:
    tn += s.encode(x["description"])

prom = "What is the capital of algeria?"
input_ = s.encode(prom)
ids = input_[0].tolist()
while True:
    logits = s.get_logits_from_input_ids(ids)
    next_t = max(range(len(logits)), key=lambda i: logits[i])
    ids.append(next_t)
    st = s.decode(next_t)
    print(st, end=" ", flush=False)
