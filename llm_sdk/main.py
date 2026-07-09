import json
from llm_sdk import Small_LLM_Model
from parser import Function, Parse
from typing import List
from structtt import Trie
import numpy as np

s = Small_LLM_Model()

Parsed = Parse()


def get_prompts():
    loaded = []
    with open("data/input/function_calling_tests.json") as file:
        loaded = json.load(file)
    prompts: List[str] = []
    for x in loaded:
        prompts.append(x["prompt"])
    return prompts


def format(Functions: List[Function]):
    to_return = []
    for x in Functions:
        returned = f"{x.name} ({x.parameters}) - {x.description}"
        to_return.append(returned)
    return to_return


def generate_super(Parsed: Parse):
    func = format(Parsed.functions)
    prompt = "<|system|> You are an AI function caller."\
            "Generate ONLY a JSON object."\
            "Use only the provided functions."\
            "No explaination, No extra talk"\
            "Allowed Functions:"\
            f"{func}"\

    return prompt

def mask_unwanted(logits, allowed_ids, numbers):
    lst = s.encode(allowed_ids).tolist()[0]
    for x in range(len(logits)):
        if [x] not in lst:
            logits[x] = float("-inf")
    return logits

def encoded_func_names(names):
    lst = []
    for x in names:
        lst.append(s.encode(x).tolist()[0])
    return lst


Tr = Trie(Parsed)
prompts = get_prompts()
for prompt in prompts:
    state = 0
    super_prompt = generate_super(Parsed)
    super_id = s.encode(super_prompt).tolist()[0]
    pro_id = s.encode(prompt).tolist()[0]
    super_id = super_id + pro_id
    n = False
    while state != float("-inf"):
        node = Tr.trie[state]
        mask = s.get_logits_from_input_ids(super_id)
        allowed_ids = list(node.keys())
        mask = mask_unwanted(mask, allowed_ids, n)
        next_t = mask.index(max(mask))
        super_id.append(next_t)
        st = s.decode(next_t)
        state = node[st]
        if state == float("-inf"):
            break
        print(st, end="", flush=True)
        n = False
    print()
