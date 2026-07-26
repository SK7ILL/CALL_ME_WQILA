import json
from typing import Any, Dict, List, Optional

from llm_sdk import Small_LLM_Model
from src.parser import Function, Parse
from src.structure import Trie


class Call:
    """Drive constrained generation over a set of parsed prompts.

    Attributes:
        Parsed: The parsed CLI arguments / function definitions.
        llm: The small LLM used for encoding, decoding and logits.
        path: Filesystem path to the vocabulary file used by ``llm``.
        dic: Mapping from token id to its decoded string.
        Tr: Trie describing the allowed token grammar.
        is_backslach: Unused flag reserved for backslash-escape tracking.
        json: Accumulated JSON-serializable results, one per prompt.
    """

    def __init__(self, Parsed: Parse, llm: Small_LLM_Model) -> None:
        """Initialize the ``Call`` helper.

        Args:
            Parsed: Parsed representation of the CLI input (functions,
                arguments, input/output file paths, etc.).
            llm: A small LLM instance exposing ``encode``, ``decode``,
                ``get_path_to_vocab_file`` and ``get_logits_from_input_ids``.
        """
        self.Parsed = Parsed
        self.llm = llm
        self.path = self.llm.get_path_to_vocab_file()
        self.dic: Dict[Any, Any] = {}
        self.own_dict()
        self.Tr = Trie(Parsed)
        self.is_backslach = False
        self.json: List[Dict[str, Any]] = []

    def format(self, Functions: List[Function]) -> List[str]:
        """Render a list of parsed functions as human-readable summaries.

        Args:
            Functions: The functions to format.

        Returns:
            A list of strings, one per function, in the form
            ``"name: description - (param: type, ...)"``.
        """
        to_return = []
        for x in Functions:
            returned = (
                f"{x.name}: {x.description} - "
                f"({self.format_params(x.parameters, len(x.parameters))}) "
            )
            to_return.append(returned)
        return to_return

    def format_params(self, params: Dict[str, Any], lenght: int) -> str:
        """Render a parameter mapping as a comma-separated ``name: type`` list.

        Args:
            params: Mapping of parameter name to a parameter object that
                exposes a ``type`` attribute.
            l: Number of entries in ``params`` (used to control trailing
                separators).

        Returns:
            A comma-separated string such as ``"a: int, b: str"``.
        """
        string = ""
        for i, x in enumerate(params):
            string += f"{x}: {params[x].type}"
            if i < lenght - 1:
                string += ", "
        return string

    def generate_super(self, Parsed: Parse) -> str:
        """Build the system/instruction prompt listing allowed functions.

        Args:
            Parsed: Parsed representation containing the available
                functions.

        Returns:
            The instruction prompt to prepend to every user prompt.
        """
        functions = self.format(Parsed.functions)
        prompt = f"""You are a precise assistant that outputs
                    structured data only.
                    Respond with valid JSON matching the required schema.
                    Do not include any text,
                    explanation, or formatting outside the JSON object.
                    Do not use markdown code
                    blocks.
                    here are the allowed function : {functions}"
                    """
        return prompt

    def get_prompts(self) -> List[str]:
        """Load the list of prompts from the configured input file.

        Returns:
            The list of prompt strings found under the ``"prompt"`` key of
            each entry in the input JSON file. Returns an empty list if the
            file cannot be found.
        """
        loaded = []
        try:
            with open(self.Parsed.arg.input) as file:
                loaded = json.load(file)
        except FileNotFoundError:
            print("Input file not found.")
        prompts: List[str] = []
        for x in loaded:
            prompts.append(x["prompt"])
        return prompts

    def own_dict(self) -> None:
        """Load the vocabulary file into ``self.dic``, keyed by token id."""
        with open(self.path) as file:
            loaded = json.load(file)
        self.dic = {}
        for _, value in loaded.items():
            self.dic[value] = s.decode(value)

    def mask_unwanted(
        self, logits: List[float], allowed_ids: Any
    ) -> List[float]:
        """Set the logits of disallowed token ids to negative infinity.

        Args:
            logits: The raw logits for every token in the vocabulary.
            allowed_ids: An iterable of token ids that are allowed. If it
                contains ``None``, no masking is applied.

        Returns:
            The (possibly mutated) logits, with disallowed ids set to
            ``float("-inf")``.
        """
        allowed_ids = set(allowed_ids)
        if None in allowed_ids:
            return logits
        for x in range(len(logits)):
            if x not in allowed_ids:
                logits[x] = float("-inf")
        return logits

    def append_tokens(self, lst: List[int], ids: List[int]) -> List[int]:
        """Append every token in ``lst`` to ``ids``.

        Args:
            lst: Token ids to append.
            ids: The destination list, mutated in place.

        Returns:
            The mutated ``ids`` list, for convenience.
        """
        for x in lst:
            ids.append(x)
        return ids

    def to_json(self, string: str, prompt: str) -> None:
        """Parse a completed JSON string and store it alongside its prompt.

        Args:
            string: The raw JSON text produced by the model.
            prompt: The original prompt that produced ``string``.
        """
        fix = json.loads(string)
        fix = {prompt: prompt, **fix}
        print(json.dumps(fix, indent=4))
        self.json.append(fix)

    def quotes_state(self, string: str) -> int:
        """Find the index of the first unescaped double quote.

        Args:
            string: The string to scan.

        Returns:
            The index of the first unescaped ``"`` character, or ``-1`` if
            none is found.
        """
        flag = False
        for i, x in enumerate(string):
            if flag:
                flag = False
                continue
            if x == "\\":
                flag = True
                continue
            if x == '"':
                return i
        return -1

    def write_to_json(self) -> None:
        """Write accumulated results to the configured output file."""
        try:
            with open(self.Parsed.arg.output, "w") as f:
                json.dump(self.json, f, indent=4)
        except BaseException as e:
            print(f"Error writing to output file: {e}")

    def main(self) -> None:
        """Run constrained generation for every configured prompt."""
        prompts = self.get_prompts()
        super_prompt = self.generate_super(Parsed)
        base_id = s.encode(super_prompt).tolist()[0]
        for prompt in prompts:
            next_state: Optional[int] = 0
            out = ""
            pro_id = s.encode(prompt).tolist()[0]
            super_id = base_id + pro_id
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
                    if '"' in string:
                        i = self.quotes_state(string)
                        splited = string[:i]
                        super_id = self.append_tokens(
                            self.llm.encode(splited).tolist()[0], super_id
                        )
                        next_state = self.Tr.trie[next_state][None]
                        string = splited
                    else:
                        super_id.append(next_t)
                out += string
                if next_state == float("-inf"):
                    self.to_json(out, prompt)
                    break
        self.write_to_json()


Parsed = Parse()
s = Small_LLM_Model(Parsed.arg.model)
model = Call(Parsed, s)
model.main()
