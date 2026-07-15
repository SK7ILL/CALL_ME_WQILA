from llm_sdk import Small_LLM_Model
import src.parser as parser
import json

Parsed = parser.Parse()
llm = Small_LLM_Model()

class Node:
    def __init__(self, i) -> None:
        self.i = i
        self.trans = {}
    def __repr__(self) -> str:
        return f"{self.trans}"
    def print(self):
        print(self.i)
path = llm.get_path_to_vocab_file()

with open(path) as file:
    loaded = json.load(file)

dic = {}

for key, value in loaded.items():
    dic[llm.decode(value)] = value

class Trie:
    def __init__(self, Parsed: parser.Parse):
        self.Parsed = Parsed
        self.Functions = Parsed.functions
        self.state = 0
        self.states = []
        self.trie = {}
        self.fixed_string = []
        self.de = {}
        self.construct()
        self.insert_all()
        self.i = 0

    def construct(self):
        for x in self.Parsed.loaded:
            params = {s : None for s in x["parameters"]}
            fix = '{"name": ' \
                  f'"{x["name"]}", '\
                  f'"parameters" : {params}'\
                  '}'
            self.fixed_string.append(fix)

    def add_state(self):
        i = len(self.states)
        self.states.append(Node(i))
        return i

    def add_to_path(self, tokens, start):
        current = start
        for x in tokens:
            i = self.states[current].trans.get(x)
            if i is None:
                i = self.add_state()
                self.states[current].trans[x] = i
            current = i
        return current

    def number_state(self, old_current):
        current = old_current
        self.states[current].trans[llm.encode("-").tolist()[0][0]] = current
        self.states[current].trans[dic["0"]] = current + 1
        for d in "123456789":
            self.states[current].trans[dic[d]] = current + 2
        old_current = self.add_state()
        self.states[old_current].trans[dic["0"]] = current + 1
        for d in "123456789":
            self.states[old_current].trans[dic[d]] = current + 2
        self.states[old_current].trans[llm.encode(".").tolist()[0][0]] = current + 3
        self.states[old_current].trans[llm.encode(",").tolist()[0][0]] = current + 5
        self.states[old_current].trans[llm.encode("}").tolist()[0][0]] = float("-inf")
        old_current = self.add_state()
        for d in "0123456789":
            self.states[old_current].trans[dic[d]] = current + 2
        self.states[old_current].trans[llm.encode(".").tolist()[0][0]] = current + 3
        self.states[old_current].trans[llm.encode(",").tolist()[0][0]] = current + 5
        self.states[old_current].trans[llm.encode("}").tolist()[0][0]] = float("-inf")
        old_current = self.add_state()
        for d in "0123456789":
            self.states[old_current].trans[dic[d]] = current + 3
        old_current = self.add_state()
        for d in "0123456789":
            self.states[old_current].trans[dic[d]] = current + 4
        self.states[old_current].trans[llm.encode(",").tolist()[0][0]] = current + 5
        self.states[old_current].trans[llm.encode("}").tolist()[0][0]] = float("-inf")
        return old_current

    def string_state(self, current):
        current = self.add_state()
        self.states[current].trans[None] = current + 1
        return current

    def states_creation(self):
        first = self.add_state()
        name = self.add_to_path(llm.encode('{"name": ').tolist()[0], first)
        for x in self.Functions:
            current = self.add_to_path(llm.encode(f'"{x.name}"').tolist()[0], name)
            current = self.add_to_path(llm.encode(',{"parameters":').tolist()[0], current)
            for p in (x.parameters):
                current = self.add_to_path(llm.encode(f' "{p}": ').tolist()[0], current)
                if x.parameters[p].type == "number":
                    current = self.number_state(current)
                    current = self.add_state()
                if x.parameters[p].type == "string":
                    current = self.string_state(current)
                    current = self.add_state()

    def insert_all(self):
        self.states_creation()
        for i in range(0, len(self.states)):
            self.trie[i] = self.states[i].trans
            self.de[i] = { llm.decode(k): self.states[i].trans[k] for k in self.states[i].trans.keys() if k is not None }

tr = Trie(Parsed)
for x in tr.trie:
    #print(x,tr.trie[x])
    print(x, tr.de[x])
