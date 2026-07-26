"""Build a token-level trie that constrains LLM generation to valid JSON.

Given a parsed set of callable functions (name + typed parameters), this
module builds a state machine (``Trie``) over the model's vocabulary so
that, at each generation step, only tokens that keep the output on a path
toward a well-formed ``{"name": ..., "parameters": {...}}`` JSON object are
allowed.
"""

from typing import Any, Dict, List, Union

import json

from llm_sdk import Small_LLM_Model
import src.parser as parser

Parsed = parser.Parse()
llm = Small_LLM_Model()


class Node:
    """A single state in the trie.

    Attributes:
        i: The numeric id of this state.
        trans: Mapping from a transition key (a character, ``True``,
            ``False``, or ``None`` for "any string content") to the id of
            the next state.
    """

    def __init__(self, i: int) -> None:
        """Initialize a node.

        Args:
            i: The numeric id assigned to this state.
        """
        self.i = i
        self.trans: Dict[Any, Any] = {}


class Trie:
    """A character-level trie/state-machine describing allowed JSON output.

    Attributes:
        Parsed: The parsed representation holding the callable functions.
        Functions: The list of parsed functions to build paths for.
        state: The current/starting state id (unused elsewhere, kept for
            compatibility).
        states: All ``Node`` instances created while building the trie.
        token_trans: Reserved for token-level transition caching (unused).
        allowed: Reserved for allowed-token tracking (unused).
        cache: Memoized results of :meth:`rehab`, keyed by state id.
        vocab: Mapping from vocabulary token id to its literal string.
        trie: Mapping from state id to its ``Node.trans`` dictionary.
        fixed_string: Precomputed skeleton strings for each function
            (unused elsewhere, kept for compatibility).
    """

    def __init__(self, Parsed: parser.Parse):
        """Initialize and fully build the trie for the given functions.

        Args:
            Parsed: Parsed representation containing the available
                functions and their loaded raw definitions.
        """
        self.Parsed = Parsed
        self.Functions = Parsed.functions
        self.state = 0
        self.states: List[Node] = []
        self.token_trans: Dict[Any, Any] = {}
        self.allowed: List[Any] = []
        self.cache: Dict[Any, Any] = {}
        self.vocab: Dict[Any, Any] = {}
        self.trie: Dict[int, Dict[Any, Any]] = {}
        self.fixed_string: List[str] = []
        self.construct()
        self.insert_all()

    def construct(self) -> None:
        """Load the vocabulary file and precompute per-function skeletons."""
        path = llm.get_path_to_vocab_file()
        with open(path) as file:
            loaded = json.load(file)
        for key, value in loaded.items():
            self.vocab[value] = key
        for x in self.Parsed.loaded:
            params = {s: None for s in x["parameters"]}
            fix = (
                '{"name": '
                f'"{x["name"]}", '
                f'"parameters" : {params}'
                "}"
            )
            self.fixed_string.append(fix.replace(" ", "Ġ"))

    def add_state(self) -> int:
        """Create a new, unconnected state.

        Returns:
            The id of the newly created state.
        """
        i = len(self.states)
        self.states.append(Node(i))
        return i

    def add_to_path(self, tokens: str, start: int) -> int:
        """Add a literal sequence of characters as a chain of transitions.

        Args:
            tokens: The characters to add, one transition per character.
            start: The state id to start the chain from.

        Returns:
            The id of the final state reached after consuming ``tokens``.
        """
        current = start
        for x in tokens:
            i = self.states[current].trans.get(x)
            if i is None:
                i = self.add_state()
                self.states[current].trans[x] = i
            current = i
        return current

    def integer_state(
            self, old_current: int, i: int, lenght: int
    ) -> Union[int, None]:
        """Build the sub-trie accepting a JSON integer value.

        Args:
            old_current: The state id to branch the integer grammar from.
            i: Index of the current parameter among its siblings.
            l: Total number of parameters for the current function.

        Returns:
            The id of the state reached after the integer (and any
            following separator) is fully consumed.
        """
        current = old_current
        self.states[current].trans["-"] = current + 1
        self.states[current].trans["0"] = current + 3
        for d in "123456789":
            self.states[current].trans[d] = current + 2
        old_current = self.add_state()
        for d in "123456789":
            self.states[old_current].trans[d] = current + 2
        old_current = self.add_state()
        for d in "0123456789":
            self.states[old_current].trans[d] = current + 2
        if i < lenght - 1:
            self.states[old_current].trans[" "] = current + 3
            self.states[old_current].trans[","] = current + 4
            old_current = self.add_state()
            self.states[old_current].trans[","] = current + 4
            return self.add_state()
        if i >= lenght - 1:
            n = self.add_state()
            self.states[current + 2].trans["}"] = current + 3
            self.states[current + 3].trans["}"] = current + 4
            # self.states[current + 2].trans["}"] = n
            m = self.add_state()
            self.states[n].trans["}"] = m
            self.states[m].trans["Ċ"] = float("-inf")
            return m
        return old_current

    def bool_state(self, old_current: int, i: int, lenght: int) -> int:
        """Build the sub-trie accepting a JSON boolean value.

        Args:
            old_current: The state id to branch the boolean grammar from.
            i: Index of the current parameter among its siblings (unused).
            l: Total number of parameters for the current function (unused).

        Returns:
            The id of the state reached after the boolean is fully
            consumed.
        """
        current = old_current
        old_current = self.add_state()
        self.states[old_current].trans['"'] = current + 2
        old_current = self.add_state()
        self.states[old_current].trans[True] = current + 3
        self.states[old_current].trans[False] = current + 3
        old_current = self.add_state()
        self.states[old_current].trans['"'] = current + 4
        return self.add_state()

    def number_state(self, old_current: int, i: int, lenght: int) -> int:
        """Build the sub-trie accepting a JSON floating-point number.

        Args:
            old_current: The state id to branch the number grammar from.
            i: Index of the current parameter among its siblings.
            l: Total number of parameters for the current function.

        Returns:
            The id of the state reached after the number (and any
            following separator) is fully consumed.
        """
        current = old_current
        self.states[current].trans["-"] = current
        self.states[current].trans["0"] = current + 1
        for d in "123456789":
            self.states[current].trans[d] = current + 1
        old_current = self.add_state()
        self.states[old_current].trans["0"] = current + 1
        for d in "123456789":
            self.states[old_current].trans[d] = current + 2
        self.states[old_current].trans["."] = current + 3
        old_current = self.add_state()
        for d in "0123456789":
            self.states[old_current].trans[d] = current + 2
        self.states[old_current].trans["."] = current + 3
        old_current = self.add_state()
        for d in "0123456789":
            self.states[old_current].trans[d] = current + 3
        if i < lenght - 1:
            self.states[old_current].trans[","] = current + 4
            return self.add_state()
        if i >= lenght - 1:
            n = self.add_state()
            self.states[old_current].trans["}"] = n
            self.states[current + 1].trans["}"] = n
            # self.states[current + 2].trans["}"] = n
            m = self.add_state()
            self.states[n].trans["}"] = m
            self.states[m].trans["Ċ"] = float("-inf")
            return m
        return old_current

    def string_state(self, current: int, i: int, lenght: int) -> int:
        """Build the sub-trie accepting a JSON string value.

        Args:
            current: The state id to branch the string grammar from.
            i: Index of the current parameter among its siblings.
            l: Total number of parameters for the current function.

        Returns:
            The id of the state reached after the string (and any
            following separator) is fully consumed.
        """
        b = self.add_state()
        a = self.add_state()
        self.states[current].trans['"'] = b
        self.states[b].trans[None] = a
        if i < lenght - 1:
            q = self.add_state()
            self.states[a].trans['"'] = q
            c = self.add_state()
            self.states[q].trans[","] = c
            e = self.add_state()
            self.states[c].trans["Ġ"] = e
            return e
        else:
            p = self.add_state()
            k = self.add_state()
            n = self.add_state()
            self.states[a].trans['"'] = p
            self.states[p].trans["}"] = k
            self.states[k].trans["}"] = n
            self.states[n].trans["Ċ"] = float("-inf")
            return n

    def states_creation(self) -> None:
        """Build the full trie: one branch per function and its parameters."""
        first = self.add_state()
        name = self.add_to_path('{"name": '.replace(" ", "Ġ"), first)
        for x in self.Functions:
            current = self.add_to_path(f'"{x.name}"'.replace(" ", "Ġ"), name)
            current = self.add_to_path(
                ', "parameters": {'.replace(" ", "Ġ"), current
            )
            for i, p in enumerate(x.parameters):
                current = self.add_to_path(
                    f'"{p}": '.replace(" ", "Ġ"), current
                )
                if x.parameters[p].type == "integer":
                    current = self.integer_state(current, i, len(x.parameters))
                if x.parameters[p].type == "string":
                    current = self.string_state(current, i, len(x.parameters))
                if x.parameters[p].type == "number":
                    current = self.number_state(current, i, len(x.parameters))
                if x.parameters[p].type == "boolean":
                    current = self.bool_state(current, i, len(x.parameters))

    def insert_all(self) -> None:
        """Populate ``self.trie`` from the built ``self.states``."""
        self.states_creation()
        for i in range(0, len(self.states)):
            self.trie[i] = self.states[i].trans

    def rehab(self, saved: int) -> Dict[Any, Any]:
        """Compute which vocabulary tokens are allowed from a given state.

        Args:
            saved: The state id to compute allowed transitions from.

        Returns:
            A mapping from allowed vocabulary token id to the resulting
            state id (or ``float("-inf")`` if that token ends generation).
            If the state accepts arbitrary string content, returns
            ``{None: saved}``.
        """
        allowed: Dict[Any, Any] = {}
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
