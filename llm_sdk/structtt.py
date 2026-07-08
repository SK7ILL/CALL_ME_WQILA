import parser


Parsed = parser.Parse()


class Node:
    def __init__(self, i) -> None:
        self.i = i
        self.trans = {}



class Trie:
    def __init__(self, functions):
        self.functions = functions
        self.state = 0
        self.states = []
        self.states.append(Node(0))
        self.trie = {}
        self.insert_all()

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
        for x in self.functions:
            self.insert(x)
        for i in range(0, len(self.states)):
            self.trie[i] = self.states[i].trans

tr = Trie(Parsed.names)
print(Parsed.names)

for x in tr.trie:
    print(x, tr.trie[x])
