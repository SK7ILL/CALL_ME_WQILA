import json
from os import wait
from llm_sdk import Small_LLM_Model
from src.parser import Function, Parse
from typing import List
from src.structure import Trie


class Call:
    def __init__(self, Parsed: Parse, llm):
        self.Parsed = Parsed
        self.llm = llm
        self.path = self.llm.get_path_to_vocab_file()
        self.dic = {}
        self.own_dict()
        self.Tr = Trie(Parsed)
        self.is_backslach = False
        self.json = []

    def format(self,Functions: List[Function]):
        to_return = []
        for x in (Functions):
            returned = f"{x.name}: {x.description} - ({self.format_params(x.parameters, len(x.parameters))}) "
            to_return.append(returned)
        return to_return

    def format_params(self, params, l):
        string = ""
        for i, x in enumerate(params):
            string += f"{x}: {params[x].type}"
            if i < l - 1:
                string += ", "
        return string

    def generate_super(self, Parsed):
        functions = self.format(Parsed.functions)
        prompt = (
                "<|system|>\n"
                "You are a function calling assistant.\n"
                "Your task is to convert the user's request into EXACTLY ONE function call.\n"
                "Use ONLY the provided functions.\n"
                "Do NOT invent function names.\n"
                "Do NOT invent parameter names.\n"
                "Copy all string parameters EXACTLY as they appear in the user's request.\n"
                "Do NOT modify, complete, rewrite, or improve any user text.\n"
                "Do NOT add placeholders, words, or values.\n"
                "Return ONLY a valid JSON object in this format:\n"
                f"Function Allowed: {functions}"
                )
        return prompt

    def get_prompts(self):
        loaded = []
        with open(self.Parsed.arg.input) as file:
            loaded = json.load(file)
        prompts: List[str] = []
        for x in loaded:
            prompts.append(x["prompt"])
        return prompts


    def own_dict(self):
        with open(self.path) as file:
            loaded = json.load(file)
        self.dic = {}
        for _, value in loaded.items():
            self.dic[value] = s.decode(value)

    def mask_unwanted(self, logits, allowed_ids):
        if None in allowed_ids:
            return logits
        for x in range(len(logits)):
            if x not in allowed_ids:
                logits[x] = float("-inf")
        return logits

    def append_tokens(self, lst, ids):
        for x in lst:
            ids.append(x)
        return ids

    def to_json(self, string, prompt):
        #string = string.replace('\\', '\\\\')
        fix = json.loads(string)
        fix["prompt"] = prompt
        self.json.append(fix)

    def print_prompt(self, prompt):
        print("-" * 40)
        print(f"PROMPT: {prompt}")

    def quotes_state(self, string):
        flag = False
        for i, x in enumerate(string):
            if flag:
                flag = False
                continue
            if x == '\\':
                flag = True
                continue
            if x == '"':
                return i
        return -1

    def write_to_json(self):
        with open(self.Parsed.arg.output, "w") as f:
            json.dump(self.json, f, indent=4)


    def main(self):
        prompts = self.get_prompts()
        super_prompt = self.generate_super(Parsed)
        print('\033[2J\033[H')
        for prompt in prompts:
            self.print_prompt(prompt)
            next_state = 0
            out = ""
            super_id = s.encode(super_prompt).tolist()[0]
            pro_id = s.encode(prompt).tolist()[0]
            super_id = super_id + pro_id
            while 1:
                mask = s.get_logits_from_input_ids(super_id)
                allowed_ids = self.Tr.rehab(next_state)
                if allowed_ids is None:
                    break
                mask = self.mask_unwanted(mask, allowed_ids.keys())
                next_t = mask.index(max(mask))
                string = self.dic[next_t]
                if None not in allowed_ids:
                    next_state = allowed_ids[next_t]
                    super_id.append(next_t)
                else:
                    if '"' in string and '\\"' not in string:
                        i = self.quotes_state(string)
                        splited = string[:i]
                        mask = self.append_tokens(self.llm.encode(splited).tolist()[0], mask)
                        next_state = self.Tr.trie[next_state][None]
                        string = splited
                    else:
                        super_id.append(next_t)
                out += string
                print(string, end="", flush=True)
                if next_state == float('-inf'):
                    self.to_json(out, prompt)
                    break
        self.write_to_json()

s = Small_LLM_Model()
Parsed = Parse()
model = Call(Parsed, s)
model.main()
