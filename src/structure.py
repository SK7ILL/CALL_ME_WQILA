from re import L
from rich import print
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



class Trie:
    def __init__(self, Parsed: parser.Parse):
        self.Parsed = Parsed
        self.Functions = Parsed.functions
        self.state = 0
        self.states = []
        self.token_trans = {}
        self.allowed = []
        self.cache = {}
        self.vocab = {}
        self.trie = {}
        self.fixed_string = []
        self.construct()
        self.insert_all()


    def construct(self):
        path = llm.get_path_to_vocab_file()
        with open(path) as file:
            loaded = json.load(file)

        for key, value in loaded.items():
            self.vocab[value] = key

        for x in self.Parsed.loaded:
            params = {s: None for s in x["parameters"]}
            fix = '{"name": ' \
                  f'"{x["name"]}", '\
                  f'"parameters" : {params}'\
                  '}'
            self.fixed_string.append(fix.replace(" ", "Ġ"))

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

    def number_state(self, old_current, i, l):
        current = old_current
        self.states[current].trans["-"] = current
        self.states[current].trans["0"] = current + 1
        for d in "123456789":
            self.states[current].trans[d] = current + 2
        old_current = self.add_state()
        self.states[old_current].trans["0"] = current + 1
        for d in "123456789":
            self.states[old_current].trans[d] = current + 2
        old_current = self.add_state()
        for d in "0123456789":
            self.states[old_current].trans[d] = current + 2
        self.states[old_current].trans['.'] = current + 3
        old_current = self.add_state()
        self.states[old_current].trans['0'] = current + 4
        if i < l - 1:
            old_current = self.add_state()
            self.states[old_current].trans[","] = current + 5
            return self.add_state()
        if i >= l - 1:
            old_current = self.add_state()
            n = self.add_state()
            self.states[old_current].trans["}"] = n
            self.states[current + 1].trans["}"] = n
            #self.states[current + 2].trans["}"] = n
            m = self.add_state()
            self.states[n].trans['}'] = m
            self.states[m].trans['Ċ'] = float('-inf')
            return m

    def float_state(self, old_current, i, l):
        current = old_current
        self.states[current].trans["-"] = current
        self.states[current].trans["0"] = current + 1
        for d in "123456789":
            self.states[current].trans[d] = current + 2
        old_current = self.add_state()
        self.states[old_current].trans["0"] = current + 1
        for d in "123456789":
            self.states[old_current].trans[d] = current + 2
        self.states[old_current].trans["."] = current + 3
        if i < l - 1:
            self.states[old_current].trans[","] = current + 5
        old_current = self.add_state()
        for d in "0123456789":
            self.states[old_current].trans[d] = current + 2
        self.states[old_current].trans["."] = current + 3
        if i < l - 1:
            self.states[old_current].trans[","] = current + 5
        old_current = self.add_state()
        for d in "0123456789":
            self.states[old_current].trans[d] = current + 3
        old_current = self.add_state()
        for d in "0123456789":
            self.states[old_current].trans[d] = current + 4
        if i < l - 1:
            self.states[old_current].trans[","] = current + 5
            return self.add_state()
        if i >= l - 1:
            n = self.add_state()
            self.states[old_current].trans["}"] = n
            self.states[current + 1].trans["}"] = n
            self.states[current + 2].trans["}"] = n
            m = self.add_state()
            self.states[n].trans['}'] = m
            self.states[m].trans['Ċ'] = float('-inf')
            return m
        return old_current

    def string_state(self, current, i, l):
        b = self.add_state()
        a = self.add_state()
        self.states[current].trans['"'] = b
        self.states[b].trans[None] = a
        if i < l - 1:
            c = self.add_state()
            self.states[a].trans[','] = c
            e = self.add_state()
            self.states[c].trans['Ġ'] = e
            return e
        else:
            p = self.add_state()
            k = self.add_state()
            n = self.add_state()
            self.states[a].trans['"'] = p
            self.states[p].trans['}'] = k
            self.states[k].trans['}'] = n
            self.states[n].trans['Ċ'] = float('-inf')
            return n

    def states_creation(self):
        first = self.add_state()
        name = self.add_to_path('{"name": '.replace(" ", "Ġ"), first)
        for x in self.Functions:
            current = self.add_to_path(f'"{x.name}"'.replace(" ", "Ġ"), name)
            current = self.add_to_path(', "parameters": {'.replace(" ", "Ġ"), current)
            for i , p in enumerate(x.parameters):
                current = self.add_to_path(f'"{p}": '.replace(" ", "Ġ"), current)
                if x.parameters[p].type == "number":
                    current = self.number_state(current, i, len(x.parameters))
                if x.parameters[p].type == "string":
                    current = self.string_state(current, i, len(x.parameters))
                if x.parameters[p].type == "float":
                    current = self.float_state(current, i, len(x.parameters))

    def insert_all(self):
        self.states_creation()
        for i in range(0, len(self.states)):
            self.trie[i] = self.states[i].trans


    def rehab(self, saved):
        allowed = {}
        if saved in self.cache:
            return self.cache[saved]
        if None in self.trie[saved]:
            return {None: saved}
        for ids in self.vocab:
            current = saved
            valid = True
            if current == float("-inf"):
                break
            for x in self.vocab[ids]:
                if current == float("-inf"):
                    break
                if x in self.trie[current]:
                    current = self.trie[current][x]
                else:
                    valid = False
                    break
            if valid:
                if current == float("-inf"):
                    allowed[ids] = float("-inf")
                else:
                    allowed[ids] = current
        self.cache[saved] = allowed
        return allowed


tr = Trie(Parsed)
print(tr.trie)
#tr.rehab(0)
#for x in tr.trie:
 #   print(x,tr.trie[x])
