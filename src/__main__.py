import json
from llm_sdk import Small_LLM_Model
from src.parser import Function, Parse
from typing import List
from src.structure import Trie


class Call:
    def __init__(self, Parsed, llm):
        self.Parsed = Parsed
        self.llm = llm
        self.path = self.llm.get_path_to_vocab_file()
        self.dic = {}
        self.own_dict()

    def format(self,Functions: List[Function]):
        to_return = []
        for x in Functions:
            returned = f"{x.name} ({x.parameters}) - {x.description}"
            to_return.append(returned)
        return to_return

    def generate_super(self, Parsed):
        func = self.format(Parsed.functions)
        prompt = f"""<|system|>
            You are a function selector.
            Choose the single best function and infer the parameter values.
            Functions:
            {func}
            User:
            """
        return prompt

    def get_prompts(self):
        loaded = []
        with open("data/input/function_calling_tests.json") as file:
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

    def generate_super1(self, Parsed: Parse):

        func = format(Parsed.functions)
        prompt = "<|system|> You are an AI function caller."\
                "Generate ONLY a JSON object."\
                "Use only the provided functions."\
                "No explaination, No extra talk"\
                "Allowed Functions:"\
                f"{func}"\

        return prompt


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


    def to_json(self, string):
        with open("test.json", "a") as to_out:
            fix = json.loads(string)
            json.dump(fix, to_out, indent=4)

    def main(self):
        Tr = Trie(Parsed)
        prompts = self.get_prompts()
        super_prompt = self.generate_super(Parsed)
        super_id = s.encode(super_prompt).tolist()[0]
        print('\033[2J\033[H')
        for prompt in prompts:
            next_state = 0
            out = ""
            pro_id = s.encode(prompt).tolist()[0]
            super_id = super_id + pro_id
            while 1:
                mask = s.get_logits_from_input_ids(super_id)
                allowed_ids = Tr.rehab(next_state)
                if allowed_ids is None:
                    break
                mask = self.mask_unwanted(mask, allowed_ids.keys())
                next_t = mask.index(max(mask))
                string = self.dic[next_t]
                if None not in allowed_ids:
                    next_state = allowed_ids[next_t]
                    super_id.append(next_t)
                else:
                    if '"' in string:
                        splited = string.replace(" ", "Ġ").split('"')
                        mask = self.append_tokens(s.encode(splited[0]).tolist()[0], mask)
                        next_state = Tr.trie[next_state][None]
                        next_t = mask.index(max(mask))
                        string = splited[0]
                    else:
                        super_id.append(next_t)
                out += string
                print(string, end="", flush=True)
                if next_state == float('-inf'):
                    self.to_json(out)
                    break

s = Small_LLM_Model()
Parsed = Parse()
model = Call(Parsed, s)
model.main()
