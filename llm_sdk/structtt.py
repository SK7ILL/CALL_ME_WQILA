import parser


Parsed = parser.Parse()

class Node:
    def __init__(self) -> None:
        self.i = 0
        self.childs = {}

class Trie:
    def __init__(self, functions):
        self.root = Node()
        self.functions = functions
        self.Create()

    def Create(self):
        for x in self.functions:
            if x not in self.root.childs:
                self.root.childs[x] = Node()
            self.root = self.root.childs[x]


tr = Trie(Parsed.names)
for x in tr.root.childs:
    print(x)
