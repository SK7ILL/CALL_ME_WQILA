from llm_sdk import Small_LLM_Model
import src.parser as parser

Parsed = parser.Parse()
llm = Small_LLM_Model()

class Node:
    def __init__(self, i) -> None:
        self.i = i
        self.trans = {}


class Trie:
    def __init__(self, Parsed: parser.Parse):
        self.Parsed = Parsed
        self.Functions = Parsed.functions
        self.state = 0
        self.states = []
        self.trie = {}
        self.fixed_string = []
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

    def insert(self):
        current = 0
        self.states.append(Node(current))
        for x in llm.encode('{"name": ').tolist()[0]:
            i = len(self.states)
            self.states.append(Node(i))
            self.states[current].trans[x] = i
            current = i
        for x in self.Functions:
            for c in llm.encode(x.name).tolist()[0]:
                print(c)
                if c in self.states[current].trans:
                    current = self.states[current].trans[c]
                else:
                    i = len(self.states)
                    self.states.append(Node(i))
                    self.states[current].trans[c] = i
                    current = i
            for s in llm.encode(' ,{"parameters":').tolist()[0]:
                if s in self.states[current].trans:
                    current = self.states[current].trans[s]
                else:
                    i = len(self.states)
                    self.states.append(Node(i))
                    self.states[current].trans[s] = i
                    current = i
            #self.states.append(Node(current))
            for p in x.parameters:
                self.states.append(Node(current + 1))
                for c in llm.encode(f' "{p}": ').tolist()[0]:
                    if c in self.states[current].trans:
                        current = self.states[current].trans[c]
                    else:
                        i = len(self.states)
                        self.states.append(Node(i))
                        self.states[current].trans[c] = current + 1
                        current += 1
                if x.parameters[p].type == "number":
                    n = "-0"
                    c = 1
                    #state 0 
                    for z in llm.encode(n).tolist()[0]:
                        if z in self.states[current].trans:
                            current = self.states[current].trans[z]
                        else:
                            self.states[current].trans[z] = current + c
                        c += 1
                        # +1 : - , +2 : 0, +3: .
                    n = "123456789"
                    for z in llm.encode(n).tolist()[0]:
                        if z in self.states[current].trans:
                            current = self.states[current].trans[z]
                        else:
                            #self.states.append(Node(current))
                            self.states[current].trans[z] = current + 2
                    #state 1 
                    self.states.append(Node(current))
                    self.states[current].trans[llm.encode("0").tolist()[0][0]] = current + 1
                    current += 1
                    for z in llm.encode(n).tolist()[0]:
                        if z in self.states[current].trans:
                            current = self.states[current].trans[z]
                        else:
                            i = len(self.states)
                            self.states[current].trans[z] = current + 1
                    #state 2 
                    #self.states.append(Node(current))
                    #self.states[current].trans[llm.encode(".").tolist()[0][0]] = current
                    n = "0123456789"
                    current += 1
                    self.states.append(Node(current))
                    for z in llm.encode(n).tolist()[0]:
                        if z in self.states[current].trans:
                            current = self.states[current].trans[z]
                        else:
                            self.states[current].trans[z] = current
                    for z in ('},'):
                        self.states[current].trans[llm.encode(z).tolist()[0][0]] = current + 1
                elif x.parameters[p].type == "string":
                    current += 1
                    self.states.append(Node(current))
                    self.states[current].trans[None] = current + 1
            current += 1
            self.states.append(Node(current))
            self.states[current].trans["\n"] = "-inf"



    def insert_all(self):
        self.insert()
        for i in range(0, len(self.states)):
            self.trie[i] = self.states[i].trans


print(llm.encode("fn_add_numbers").tolist()[0])
print(llm.decode(llm.encode("fn_add_numbers").tolist()[0][2]))

tr = Trie(Parsed)
for x in tr.trie:
    print(x,tr.trie[x])
