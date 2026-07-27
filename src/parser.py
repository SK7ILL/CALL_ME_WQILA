"""Parse CLI arguments and the JSON function-definition file.

Defines the ``Function``/``Param`` schema (via pydantic) describing a
callable function's name, description, typed parameters and return type,
and a ``Parse`` helper that reads CLI arguments and loads/validates the
function definitions file into a list of ``Function`` objects.
"""

import argparse
import json
from typing import List

from pydantic import BaseModel


class Param(BaseModel):
    """A single function parameter or return value's type descriptor.

    Attributes:
        type: The declared type name (e.g. ``"integer"``, ``"string"``).
    """

    type: str


class Function(BaseModel):
    """A parsed, schema-validated callable function definition.

    Attributes:
        name: The function's name (expected to start with ``"fn_"``).
        description: A human-readable description of the function.
        parameters: Mapping from parameter name to its ``Param`` schema.
        returns: The function's return type schema.
    """

    name: str
    description: str
    parameters: dict[str, Param]
    returns: Param


class Parse:
    """Parse CLI arguments and load/validate function definitions.

    Attributes:
        loaded: Raw JSON records loaded from the functions-definition file.
        names: Names of every successfully parsed function.
        functions: Validated ``Function`` instances.
        arg: The parsed ``argparse.Namespace`` of CLI arguments.
    """

    def __init__(self) -> None:
        """Initialize by parsing CLI arguments and loading definitions."""
        self.loaded: List[dict] = []
        self.names: List[str] = []
        self.functions: List[Function] = []
        self.arging()
        self.reading()

    def arging(self) -> None:
        """Parse CLI arguments into ``self.arg``.

        Recognized arguments:
            --functions_definition: Path to the functions-definition JSON
                file (default: ``data/input/functions_definition.json``).
            --input: Path to the prompts input JSON file (default:
                ``data/input/function_calling_tests.json``).
            --output: Path to the JSON file results are written to
                (default: ``data/output/function_calls.json``).
        """
        parsed = argparse.ArgumentParser()
        parsed.add_argument("--functions_definition",
                            type=str,
                            default="data/input/functions_definition.json")

        parsed.add_argument("--input",
                            type=str,
                            default="data/input/function_calling_tests.json")

        parsed.add_argument("--output",
                            type=str,
                            default="data/output/function_calls.json")
        parsed.add_argument("--model",
                            type=str,
                            default="Qwen/Qwen3-0.6B")
        self.arg = parsed.parse_args()

    def reading(self) -> None:
        """Load the functions-definition file and validate each entry.

        Populates ``self.loaded`` with the raw JSON records, ``self.names``
        with each function's name, and ``self.functions`` with validated
        ``Function`` instances.

        Raises:
            ValueError: If a function's name does not start with ``"fn_"``.
        """
        try:
            with open(self.arg.functions_definition, "r") as file:
                self.loaded = json.load(file)
        except BaseException:
            print("Error Reading the file")
        for x in self.loaded:
            if not x['name'].startswith("fn_"):
                raise ValueError
            function = Function(**x)
            self.functions.append(function)
            self.names.append(x['name'])
