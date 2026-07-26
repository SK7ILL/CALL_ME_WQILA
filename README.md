# Constrained JSON Function-Calling Decoder
 
## Description
 
This project forces a small language model to produce **syntactically
guaranteed, schema-valid JSON function calls** — the
`{"name": ..., "parameters": {...}}` objects used for LLM "tool use" / function
calling — without relying on the model to get the JSON syntax right on its
own and without any retry/regeneration loop.
 
Instead of asking the model to freely generate JSON and hoping it's valid,
the project compiles the set of allowed functions (names, parameter names,
and parameter types) into a **token-level trie / state machine**. At every
generation step, the model's logits are masked so that only tokens which
keep the output on a path toward a valid call are ever selectable. The
result is output that is JSON-valid *by construction*, restricted to one of
a known set of functions with correctly typed arguments.
 
The project has three components:
 
| File | Role |
|---|---|
| `parser.py` | Parses CLI arguments and loads/validates the function-definition file into typed `Function`/`Param` objects (via `pydantic`). |
| `structure.py` | Builds the `Trie`: a character-level state machine encoding every valid `{"name": ..., "parameters": {...}}` output for the parsed functions. |
| `call.py` | Runs the constrained decoding loop: for each input prompt, walks the trie token-by-token against the model's logits, and writes the resulting function calls to a JSON file. |
 
## Instructions
 
### Requirements
 
- Python 3.9+ (the codebase uses the built-in `dict[str, Param]` generic
  syntax, which requires 3.9+, or `from __future__ import annotations` on
  earlier versions).
- [`pydantic`](https://docs.pydantic.dev/) — schema validation for function
  definitions.
- [`rich`](https://rich.readthedocs.io/) — pretty-printing (`structure.py`).
- `llm_sdk` — an internal/private package exposing `Small_LLM_Model`, with
  `encode`, `decode`, `get_path_to_vocab_file`, and
  `get_logits_from_input_ids`. This is not on PyPI; install it from wherever
  your team distributes it (private index, wheel, or local path) before
  running anything below.
### Installation
 
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install pydantic rich
pip install <path-or-index-to-llm_sdk>
```
 
### Expected input files
 
`parser.py` expects a functions-definition JSON file — a list of objects
matching the `Function` schema:
 
```json
[
  {
    "name": "fn_get_weather",
    "description": "Get the current weather for a city.",
    "parameters": {
      "city": { "type": "string" },
      "days": { "type": "integer" }
    },
    "returns": { "type": "string" }
  }
]
```
 
Function names **must** start with `fn_`; the parser raises `ValueError`
otherwise.
 
The prompts input file is a JSON list of objects with a `"prompt"` key:
 
```json
[
  { "prompt": "What's the weather in Rabat for the next 3 days?" }
]
```
 
### Running
 
```bash
python call.py \
  --functions_definition data/input/functions_definition.json \
  --input data/input/function_calling_tests.json \
  --output data/output/function_calls.json
```
 
All three arguments are optional and default to the paths shown above
(see `Parse.arging` in `parser.py`).
 
`structure.py` can also be run on its own to inspect the trie that would be
built for a given function-definition file:
 
```bash
python structure.py --functions_definition data/input/functions_definition.json
```
 
It prints the full `state -> transitions` mapping via `rich.print`.
 
## Algorithm Explanation — Constrained Decoding
 
The core idea is **grammar-constrained greedy decoding**, implemented as a
character-level trie walked in lockstep with the model's subword
vocabulary:
 
1. **Grammar compilation (`Trie.states_creation`)**
   For every parsed function, a chain of trie states is built character by
   character for the fixed parts of the output — `{"name": "fn_...",
   "parameters": {"param_name": ` — using `add_to_path`. For each
   parameter, a type-specific sub-grammar is appended:
   - `string_state` — a quote, an arbitrary-content state (see below), a
     closing quote, then either `, ` (more parameters follow) or `}}`
     (last parameter, closes both the `parameters` and outer objects).
   - `integer_state` / `number_state` — hand-built digit automata
     (optional leading `-`, no leading zero except `0` itself,
     `number_state` additionally allows a decimal point and further
     digits), followed by the same "more params vs. closing braces" fork.
   - `bool_state` — accepts the literal tokens `True`/`False` between
     quotes.
   Every terminal path ends in a special transition on the newline token
   (`"Ċ"`, GPT‑2‑style BPE for `\n`) to `float("-inf")`, which acts as an
   explicit **end-of-generation sentinel** state.
2. **Vocabulary loading (`Trie.construct`)**
   The model's vocabulary file is loaded once and inverted into
   `self.vocab: token_id -> literal string`, so that whole subword tokens
   (not just single characters) can be validated against the trie.
3. **Per-step token masking (`Trie.rehab`)**
   Given the current state, `rehab` scans the *entire* vocabulary and, for
   every candidate token, walks its literal string through the trie one
   character at a time. A token is **allowed** only if every character in
   it corresponds to an existing transition from the current state. This
   yields `{token_id: next_state}` for every valid next token. If the
   current state instead has a `None` transition (meaning "arbitrary
   string content is allowed here"), `rehab` short-circuits and returns
   `{None: saved}` immediately.
4. **Logit masking and selection (`Call.mask_unwanted`, `Call.main`)**
   The raw logits from the model are set to `-inf` for every token not in
   the allowed set, and the highest-scoring remaining token is picked
   (`mask.index(max(mask))`) — i.e. **greedy, deterministic decoding**
   restricted to the allowed set.
5. **Free-text string handling**
   When the current state accepts arbitrary content (the `None`
   transition), the chosen token's decoded string is scanned
   character-by-character (`Call.quotes_state`) for the first *unescaped*
   `"`. If found, only the portion of the token *before* the quote is kept
   and appended, the trie is advanced to the state that follows a closing
   quote (`self.Tr.trie[next_state][None]`), and generation resumes from
   there — effectively letting the model write free-form string values
   while still detecting exactly when the string ends.
6. **Termination**
   Once the walked state equals `float("-inf")`, generation for that
   prompt stops, the accumulated output string is parsed as JSON
   (`Call.to_json`), the originating prompt is attached to the record, and
   the result is appended to the output list.
## Design Decisions
 
- **Constrain, don't validate-and-retry.** Building the grammar up front
  and masking logits guarantees valid syntax on the first pass, instead of
  generating freely and re-prompting on parse failure (slower, and not
  guaranteed to converge).
- **Character-level trie over a subword vocabulary.** The model's
  tokenizer doesn't align to single characters, so every candidate
  vocabulary token is re-validated character-by-character against the trie
  on every step (see Performance Analysis below for the cost of this
  choice) rather than trying to pre-index whole tokens per state.
- **Explicit sentinel state for termination.** Using `float("-inf")` as a
  real, addressable state (rather than a boolean flag) lets the "end of
  generation" condition flow through the same `state -> transition`
  machinery as everything else.
- **Separation of concerns.** Schema parsing/validation (`parser.py`),
  grammar construction (`structure.py`), and the decoding loop (`call.py`)
  are kept in separate modules so the grammar can be built, printed, and
  debugged independently of running the model.
- **Greedy decoding.** `mask.index(max(mask))` always takes the
  single best allowed token — simple and fully deterministic, at the cost
  of not exploring alternative completions (no beam search / sampling).
- **`fn_` naming convention enforced at parse time.** `Parse.reading` raises
  `ValueError` on any function name not prefixed with `fn_`, catching
  definition-file mistakes immediately instead of letting them reach the
  trie builder.
## Performance Analysis
 
- **Speed.** `Trie.rehab` iterates over the *entire* vocabulary and, for
  each candidate token, walks every character of that token's decoded
  string through the trie. This is `O(vocab_size × avg_token_length)`
  **per generation step**, and it runs once per token actually emitted.
  For a vocabulary of tens of thousands of tokens, this is the dominant
  cost of the whole pipeline. A `self.cache` dict exists in `Trie` for
  memoizing `rehab(state)` results, but the cache lookup is currently
  commented out in `rehab`, so results are recomputed from scratch every
  time a state is revisited — an easy win if re-enabled.
- **Accuracy / reliability of the JSON produced.** Because every emitted
  character comes from a masked, grammar-restricted logit distribution,
  the output is **syntactically valid JSON by construction** — it cannot
  drift into malformed braces, missing commas, or unterminated strings for
  the fixed (non-string-content) parts of the grammar. The main residual
  risk is *semantic*, not syntactic: greedy decoding always takes the
  model's top allowed token, so if the model's raw preferences are wrong
  for a given prompt (wrong function, wrong parameter value), constrained
  decoding will still produce valid-but-incorrect JSON rather than
  invalid JSON.
- **Determinism.** No sampling temperature or beam search is used, so the
  same prompt against the same model and function set will always produce
  the same output — useful for reproducibility and testing, but it also
  means there's no mechanism to recover from a bad greedy choice partway
  through generation.
- **Operational reliability.** A couple of implementation details reduce
  robustness independent of the algorithm: `Call.write_to_json` and
  `Parse.reading` both use broad `except` clauses that print an error and
  continue rather than surfacing the failure, which can mask real problems
  (e.g. a missing input file silently yielding zero parsed functions).
## Challenges Faced
 
- **Subword tokens vs. a character-level grammar.** The model doesn't
  generate one character at a time — it generates BPE subword tokens that
  can span multiple grammar transitions (e.g. a single token might contain
  several digits, or a comma *and* a space). The solution was to validate
  each *entire* candidate token against the trie character-by-character
  before allowing it, rather than trying to build the trie at the token
  level.
- **Free-form string values inside a strict grammar.** Parameter values of
  type `string` can contain arbitrary text, which can't be pre-compiled
  into the trie. This was solved with a special `None` transition meaning
  "accept anything here", combined with `quotes_state` to detect the
  first *unescaped* closing quote inside a token that may mix string
  content with the terminating `"` — splitting the token so only the
  content up to (not including) the quote is emitted.
- **BPE special characters.** The tokenizer represents spaces and newlines
  as literal characters in its vocabulary (`Ġ` for a leading space, `Ċ` for
  a newline) rather than the plain characters themselves. All literal
  strings inserted into the trie (`add_to_path`) have to be translated
  (`.replace(" ", "Ġ")`) to match, and the newline token `Ċ` had to be
  used explicitly to detect generation and drive the transition to the
  `-inf` termination state.
- **Branching grammar per parameter position.** Whether a parameter is
  followed by `, "next_param": ` or by `}}` depends on whether it's the
  last parameter of its function, so every typed sub-grammar
  (`integer_state`, `number_state`, `string_state`) has to branch on
  `i < l - 1` vs. `i >= l - 1` and wire up a different set of closing
  transitions for each case.
## Testing Strategy
 
The repository does not currently ship an automated test suite. The
approach used/recommended for validating this implementation is:
 
1. **Grammar inspection.** Run `structure.py` directly against a small,
   hand-written function-definition file and inspect the printed
   `state -> transitions` mapping to confirm each parameter type produces
   the expected branches (comma-continuation vs. closing-brace paths).
2. **Golden-path end-to-end runs.** Run `call.py` against a small set of
   prompts with an unambiguous expected function/parameter combination and
   confirm the output file parses as valid JSON and matches the expected
   `name`/`parameters`.
3. **Type coverage.** Exercise at least one function definition per
   supported parameter type (`string`, `integer`, `number`, `boolean`) and
   at least one function with multiple parameters, to cover both the
   "more parameters follow" and "last parameter" branches of the grammar.
4. **Edge cases worth adding explicit tests for:**
   - Strings containing an escaped quote (`\"`), to exercise
     `quotes_state`'s escape handling.
   - Negative and multi-digit integers/numbers, and numbers with a decimal
     point.
   - A function-definition file containing a name that does *not* start
     with `fn_`, to confirm `Parse.reading` raises `ValueError`.
   - A missing/invalid input or definitions file, to confirm the (current,
     silent) error-handling behavior is what's actually wanted.
## Example Usage
 
Given `data/input/functions_definition.json`:
 
```json
[
  {
    "name": "fn_get_weather",
    "description": "Get the current weather for a given city.",
    "parameters": {
      "city": { "type": "string" },
      "days": { "type": "integer" }
    },
    "returns": { "type": "string" }
  }
]
```
 
and `data/input/function_calling_tests.json`:
 
```json
[
  { "prompt": "What's the weather like in Rabat for the next 3 days?" }
]
```
 
running:
 
```bash
python call.py \
  --functions_definition data/input/functions_definition.json \
  --input data/input/function_calling_tests.json \
  --output data/output/function_calls.json
```
 
produces `data/output/function_calls.json` containing entries of the form:
 
```json
[
  {
    "prompt": "What's the weather like in Rabat for the next 3 days?",
    "name": "fn_get_weather",
    "parameters": { "city": "Rabat", "days": 3 }
  }
]
```
 
## Resources
 
**References on the underlying techniques:**
- [pydantic documentation](https://docs.pydantic.dev/) — data validation
  and settings management used for the `Function`/`Param` schema.
- [Python `argparse` documentation](https://docs.python.org/3/library/argparse.html) —
  CLI argument parsing used in `Parse.arging`.
- [GPT-2 BPE tokenizer / `encoder.json` format](https://github.com/openai/gpt-2) —
  background on the `Ġ`/`Ċ` byte-pair-encoding conventions used when
  building literal trie paths.
- General background on **grammar-constrained / structured decoding** for
  LLMs (the family of techniques this project implements a small, from-scratch
  version of): finite-state or context-free-grammar-constrained decoding,
  and logit masking against a set of allowed next tokens.
- [Trie (prefix tree) — general data structure reference](https://en.wikipedia.org/wiki/Trie).
**Use of AI:**
- An AI assistant (Claude) was used in this project for **documentation and
  code hygiene**, specifically: adding docstrings and type hints to
  `parser.py`, `structure.py`, and `call.py`; reformatting the three files
  to comply with `flake8` and `mypy` . The AI was explicitly instructed not to alter existing logic,
  function/variable names, or behavior — only to add documentation,
  annotations, and formatting, and to flag (rather than silently fix)
  pre-existing bugs it noticed along the way. 
