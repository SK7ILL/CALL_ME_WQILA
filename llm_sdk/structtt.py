import parser


Parsed = parser.Parse()


class Node:
    def __init__(self, i) -> None:
        self.i = i
        self.trans = {}


class Trie:
    def __init__(self, Parsed):
        self.Parsed = Parsed
        self.state = 0
        self.states = []
        self.states.append(Node(0))
        self.trie = {}
        self.fixed_string = []
        self.construct()
        self.insert_all()

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
        for x in tokens:
            for c in x:
                if c in self.states[current].trans:
                    current = self.states[current].trans[c]
                else:
                    i = len(self.states)
                    self.states.append(Node(i))
                    self.states[current].trans[x] = i
                    current = i

    def insert_all(self):
        for x in self.fixed_string:
            self.insert(x)
        for i in range(0, len(self.states)):
            if not self.states[i].trans:
                self.trie[i] = float("-inf")
            else:
                self.trie[i] = self.states[i].trans
