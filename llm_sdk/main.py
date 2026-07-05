from collections import Counter
from llm_sdk import Small_LLM_Model
import json
from parser import Parse

s = Small_LLM_Model()

Parsed = Parse()

ids = s.encode(Parsed.functions[0].description)
ids = ids.tolist()[0]

allowed = set()
for x in Parsed.names:
    ids = s.encode(x).tolist()[0]
    allowed.update(ids)


while True:
    logits = s.get_logits_from_input_ids(ids)
    for i in range(len(logits)):
        if i not in allowed:
            logits[i] = -float("inf")
    next_t = max(range(len(logits)), key=lambda i: logits[i])
    ids.append(next_t)
    st = s.decode(next_t)
    print(st, end="", flush=False)
