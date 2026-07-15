import json
from llm_sdk import Small_LLM_Model
from src.parser import Function, Parse
from typing import List
from src.structtt import Trie

s = Small_LLM_Model()

Parsed = Parse()

def format(Functions: List[Function]):
    to_return = []
    for x in Functions:
        returned = f"{x.name} ({x.parameters}) - {x.description}"
        to_return.append(returned)
    return to_return

def generate_super(Parsed):
    func = format(Parsed.functions)
    prompt = f"""<|system|>
        You are a function-calling engine. Your ONLY job is to output a single JSON object that calls one function using the schema below.

        AVAILABLE FUNCTIONS:
        {func}

        OUTPUT RULES:
        1. Output ONLY the JSON object. No explanation, no markdown, no code fences, no extra text before or after.
        2. The JSON must have exactly this shape:
           {{"name": "<function_name>", "parameters": {{"<param1>": <value1>, ...}}}}
        3. Choose the single function that best matches the user's request. Use only function names and parameter names from the list above — never invent new ones.
        4. Fill every required parameter. If a value is unknown and the parameter is optional, omit it. If a value is unknown and the parameter is required, make the most reasonable inference from the user's request.
        5. Match each parameter's type exactly:
           - strings go in double quotes
           - numbers are written bare, no quotes
           - booleans are 'true' or 'false', no quotes
           - null is written as 'null', no quotes
        6. Generate the object left to right, one token at a time, in this fixed order: opening brace, "name" key, function name, "parameters" key, opening brace for parameters, each parameter key and value in the order listed in the schema, closing brace for parameters, closing brace.
        7. Never restate the schema, never explain your choice, never add trailing text after the final closing brace.

        Begin the JSON object now.
        <|end|>
        """
    return prompt

def get_prompts():
    loaded = []
    with open("data/input/function_calling_tests.json") as file:
        loaded = json.load(file)
    prompts: List[str] = []
    for x in loaded:
        prompts.append(x["prompt"])
    return prompts


path = s.get_path_to_vocab_file()

with open(path) as file:
    loaded = json.load(file)

dic = {}

for key, value in loaded.items():
    dic[value] = s.decode(value)

def generate_super1(Parsed: Parse):
    func = format(Parsed.functions)
    prompt = "<|system|> You are an AI function caller."\
            "Generate ONLY a JSON object."\
            "Use only the provided functions."\
            "No explaination, No extra talk"\
            "Allowed Functions:"\
            f"{func}"\

    return prompt



def mask_unwanted(logits, allowed_ids):
    if allowed_ids == [None]:
        return logits
    for x in range(len(logits)):
        if x not in allowed_ids:
            logits[x] = float("-inf")
    return logits

def encoded_func_names(names):
    lst = []
    for x in names:
        lst.append(s.encode(x).tolist()[0])
    return lst

print('\033[2J\033[H')

Tr = Trie(Parsed)
prompts = get_prompts()
for prompt in prompts:
    state = 0
    super_prompt = generate_super(Parsed)
    super_id = s.encode(super_prompt).tolist()[0]
    pro_id = s.encode(prompt).tolist()[0]
    super_id = super_id + pro_id
    n = False
    while 1:
        node = Tr.trie[state]
        mask = s.get_logits_from_input_ids(super_id)
        allowed_ids = list(node.keys())
        mask = mask_unwanted(mask, allowed_ids)
        next_t = mask.index(max(mask))
        super_id.append(next_t)
        st = s.decode(next_t)
        state = node.get(next_t)
        if state is None:
            state = node.get(None)
            if '}' in st:
                state = float("-inf")
        print(st, end="", flush=True)
        if state == float("-inf"):
            break
    print()
