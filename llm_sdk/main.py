from enum import Enum, auto
import json
from os import stat
from llm_sdk import Small_LLM_Model
from parser import Function, Parse
from typing import List

s = Small_LLM_Model()

Parsed = Parse()

class State(Enum):
    START = auto()
    OPEN_BRACE = auto()
    NAME_KEY = auto()
    NAME_COLON = auto()
    FUNCTION_NAME = auto()
    COMMA = auto()
    PARAMETERS_KEY = auto()
    PARAMETERS_COLON = auto()
    OPEN_PARAMETERS = auto()
    PARAMETER_NAME = auto()
    PARAMETER_COLON = auto()
    PARAMETER_VALUE = auto()
    NEXT_PARAMETER = auto()
    CLOSE_PARAMETERS = auto()
    CLOSE_OBJECT = auto()
    DONE = auto()


def get_prompts():
    loaded = []
    with open("data/input/function_calling_tests.json") as file:
        loaded = json.load(file)
    prompts: List[str] = []
    for x in loaded:
        prompts.append(x["prompt"])
    return prompts

def functions_design(Parsed: Parse):
    functions: dict[str, str] = {}
    lst = []
    for x in Parsed.functions:
        designed: str = ""
        designed = f"{x.name} ({x.parameters}) - {x.description} -> {x.returns}"
        lst.append(designed)
        functions[x.name] = designed
    return lst

def generate_super(pr):
    prompt= "<|system|> You are an AI function caller."\
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


for prompt in prompts:
    state = FSM()
    func_name = None
    super_prompt = generate_super(prompt)
    super_id = s.encode(super_prompt).tolist()[0]
    pro_id = s.encode(prompt).tolist()[0]
    super_id = super_id + pro_id
    while state.stat != State.DONE:
        logits = s.get_logits_from_input_ids(super_id)
        allowed = get_allowed_tokens(state.stat , Parsed, func_name)
        logits = mask_unwanted(logits, allowed)
        next_t = logits.index(max(logits))
        super_id.append(next_t)
        st = s.decode(next_t)
        if state == State.FUNCTION_NAME:
            name = st
            for x in Parsed.functions:
                if x.name == name:
                    func_name = x
                    break
        state.update()
        print(st, end="", flush=True)
    print()
