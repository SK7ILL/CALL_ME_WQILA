from enum import Enum, auto
import json
import sys 
from llm_sdk import Small_LLM_Model
from parser import Function, Parse
from typing import List

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


def generate_super(pr):
    prompt = "<|system|> You are an AI function caller."\
            "Generate ONLY a JSON object."\
            'Schema:{"name": "<allowed function>", "parameters": { ... }}'\
            "Use only the provided functions."\
            "Do not answer the question directly."\
            "Do not generate explanations."\
            f"<|user|>{pr}"\
            "{"

    return prompt


ids = s.encode(Parsed.functions[0].description)
ids = ids.tolist()[0]

allowed = set()

for x in Parsed.names:
    allowed.update(s.encode(x).tolist()[0])


voc = []

path = s.get_path_to_tokenizer_file()

class FSM:
    def __init__(self) -> None:
        self.stat = State.START

    def update(self) -> None:
        stats = list(self.stat.__class__)
        i = stats.index(self.stat)
        self.stat = stats[i + 1]

def get_allowed_tokens(state, parser, function=None):
    if state == State.START:
        return set(s.encode("{").tolist()[0])
    elif state == State.OPEN_BRACE:
        return set(s.encode('"name"').tolist()[0])
    elif state == State.NAME_COLON:
        return set(s.encode(":").tolist()[0])
    elif state == State.FUNCTION_NAME:
        allowed = set()
        for name in parser.names:
            allowed.update(s.encode(name).tolist()[0])
        return allowed
    elif state == State.COMMA:
        return set(s.encode(",").tolist()[0])
    elif state == State.PARAMETERS_KEY:
        return set(s.encode('"parameters"').tolist()[0])
    elif state == State.PARAMETERS_COLON:
        return set(s.encode(":").tolist()[0])
    elif state == State.OPEN_PARAMETERS:
        return set(s.encode("{").tolist()[0])
    elif state == State.PARAMETER_NAME:
        allowed = set()
        if function is not None:
            for p in function.parameters:
                allowed.update(s.encode(p).tolist()[0])
        return allowed
    elif state == State.PARAMETER_COLON:
        return set(s.encode(":").tolist()[0])
    elif state == State.CLOSE_PARAMETERS:
        return set(s.encode("}").tolist()[0])
    elif state == State.CLOSE_OBJECT:
        return set(s.encode("}").tolist()[0])
    return set()


def mask_unwanted(logits, allowed):
    for x in range(len(logits)):
        if x not in allowed:
            logits[x] = float("-inf")
    return logits

prompts = get_prompts()


def done(prefix):
    function = encoded_func_names(Parsed.names)
    for f in function:
        if prefix == f:
            return f
    return None


def encoded_func_names(names):
    lst = []
    for x in names:
        lst.append(s.encode(x).tolist()[0])
    return lst

for prompt in prompts:
    state = FSM()
    prefix = []
    func_name = None
    super_prompt = generate_super(prompt)
    super_id = s.encode(super_prompt).tolist()[0]
    pro_id = s.encode(prompt).tolist()[0]
    super_id = super_id + pro_id
    while state.stat != State.DONE:
        logits = s.get_logits_from_input_ids(super_id)
        allowed = get_allowed_tokens(state.stat, Parsed, func_name)
        logits = mask_unwanted(logits, allowed)
        next_t = logits.index(max(logits))
        super_id.append(next_t)
        prefix.append(next_t)
        is_done = done(prefix)
        if is_done:
            func_name = is_done
        st = s.decode(next_t)
        state.update()
        print(st, end="", flush=True)
    print()
