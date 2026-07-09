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

def mask_unwanted(logits, allowed_ids):
    mask = np.full(len(logits), float("-inf"))
    mask[list(allowed_ids)] = 0
    return logits + mask

def encoded_func_names(names):
    lst = []
    for x in names:
        lst.append(s.encode(x).tolist()[0])
    return lst

Tr = Trie(Parsed)
print(Tr.trie)
prompts = get_prompts()
for prompt in prompts:
    state = 0
    prefix = []
    super_prompt = generate_super(Parsed)
    super_id = s.encode(super_prompt).tolist()[0]
    pro_id = s.encode(prompt).tolist()[0]
    super_id = super_id + pro_id
    while state != float("-inf"):
        logits = s.get_logits_from_input_ids(super_id)
        logits = mask_unwanted(logits, Tr.trie[state])
        next_t = logits.index(max(logits))
        state = Tr.trie[state].get(next_t)
        super_id.append(next_t)
        prefix.append(next_t)
        st = s.decode(next_t)
        print(st, end="", flush=True)
    print()
