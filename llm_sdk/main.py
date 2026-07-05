from llm_sdk import Small_LLM_Model
import json
from parser import Function


s = Small_LLM_Model()
loaded = []
try:
    with open("data/input/functions_definition.json", "r") as file:
        loaded = json.load(file)
except BaseException as e:
    print(e)

lst = []
for x in loaded:
    fun = Function(**x)
    lst.append(fun)

print(lst)

call  = []
with open("data/input/function_calling_tests.json") as file:
    call = json.load(file)


promt = []
for x in call:
    promt.append(x["prompt"])
ids = s.encode(promt[3])
ids = ids.tolist()[0]

while True:
    logits = s.get_logits_from_input_ids(ids)
    next_t = max(range(len(logits)), key=lambda i: logits[i])
    ids.append(next_t)
    st = s.decode(next_t)
    print(st, end="", flush=False)
