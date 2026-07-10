import src.parser as parser

Parsed = parser.Parse()

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
        self.states.append(Node(0))
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

    def insert(self, tokens):
        current = 0
        for x in '{"name": '.replace(" ", "Ġ"):
            i = len(self.states)
            self.states.append(Node(i))
            self.states[current].trans[x] = i
            current = i

        for x in self.Functions:
            for name in x.name:
                for c in name.replace(" ", "Ġ"):
                    if c in self.states[current].trans:
                        current = self.states[current].trans[c]
                    else:
                        i = len(self.states)
                        self.states.append(Node(i))
                        self.states[current].trans[c] = i
                        current = i
            for s in ',{"parameters: '.replace(" ", "Ġ"):
                if s in self.states[current].trans:
                    current = self.states[current].trans[s]
                else:
                    i = len(self.states)
                    self.states.append(Node(i))
                    self.states[current].trans[s] = i
                    current = i
            self.states.append(Node(current + 1))
            self.states[current + 1].trans[":"] = current + 2
            current += 1
            for p in x.parameters:
                for c in f'"{p}": '.replace(" ", "Ġ"):
                    if c in self.states[current].trans:
                        current = self.states[current].trans[c]
                    else:
                        i = len(self.states)
                        self.states.append(Node(i))
                        self.states[current].trans[c] = i
                        current = i
                if x.parameters[p].type == "number":
                    n = "-0"
                    c = 1
                    #state 0 
                    for z in n:
                        if z in self.states[current].trans:
                            current = self.states[current].trans[z]
                        else:
                            i = len(self.states)
                            self.states.append(Node(i))
                            self.states[current].trans[z] = current + c
                        c += 1
                        # +1 : - , +2 : 0, +3: .
                    n = "123456789"
                    for z in n:
                        if z in self.states[current].trans:
                            current = self.states[current].trans[z]
                        else:
                            i = len(self.states)
                            self.states.append(Node(i))
                            self.states[current].trans[z] = current + 3
                    current += 1
                    #state 1 
                    self.states.append(Node(current))
                    self.states[current].trans["0"] = current + 1
                    for z in n:
                        if z in self.states[current].trans:
                            current = self.states[current].trans[z]
                        else:
                            i = len(self.states)
                            self.states.append(Node(i))
                            self.states[current].trans[z] = current + 2
                    current += 1
                    #state 2 
                    self.states.append(Node(current))
                    self.states[current].trans["."] = current + 2
                    current += 1
                    self.states.append(Node(current))
                    self.states[current].trans["."] = current + 2
                    n = "0123456789"
                    for z in n:
                        if z in self.states[current].trans:
                            current = self.states[current].trans[z]
                        else:
                            i = len(self.states)
                            self.states.append(Node(i))
                            self.states[current].trans[z] = current
                    current += 1
                    for z in n:
                        if z in self.states[current].trans:
                            current = self.states[current].trans[z]
                        else:
                            i = len(self.states)
                            self.states.append(Node(i))
                            self.states[current].trans[z] = current + 1
                    current += 1
                    for z in n:
                        if z in self.states[current].trans:
                            current = self.states[current].trans[z]
                        else:
                            i = len(self.states)
                            self.states.append(Node(i))
                            self.states[current].trans[z] = current
                    for z in "},":
                        self.states.append(Node(current))
                        self.states[current].trans[z] = current

                elif x.parameters[p].type == "string":
                    self.states.append(Node(len(self.states)))
                    self.states[current].trans["None"] = current + 1
                    for z in "},":
                        self.states.append(Node(len(self.states)))
                        self.states[current].trans[z] = current + 1
                current += 1

    def insert_all(self):
        for x in self.fixed_string:
            self.insert(x)
        for i in range(0, len(self.states)):
            self.trie[i] = self.states[i].trans

tr = Trie(Parsed)
for x in tr.trie:
    print(x,tr.trie[x])
