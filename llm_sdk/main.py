from llm_sdk import Small_LLM_Model
import json

s = Small_LLM_Model()






loaded = []
try:
    with open("data/input/functions_definition.json", "r") as file:
        loaded = json.load(file)
except BaseException as e:
    print(e)

data = {}
for function in loaded:
    data[function["name"]] = function



def check_valid_name(name: str) -> bool:
    return (name in data.keys())



call  = []
with open("data/input/function_calling_tests.json") as file:
    call = json.load(file)


promt = []
for x in call:
    promt.append(x["prompt"])

for x in promt:
    ids = s.encode(x)
    ids = ids[0].tolist()
    while True:
        logits = s.get_logits_from_input_ids(ids)
        next_t = max(range(len(logits)), key=lambda i: logits[i])
        ids.append(next_t)
        st = s.decode(next_t)
        print(st, end="", flush=False)
