import json
from typing import List
from pydantic import BaseModel
import argparse

class Param(BaseModel):
    type: str

class Function(BaseModel):
    name: str
    description: str
    parameters: dict[str, Param]
    returns: Param


class Parse:
    def __init__(self):
        self.loaded: List[dict] = []
        self.names: List[str] = []
        self.functions: List[Function] = []
        self.arging()
        self.reading()

    def arging(self):
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
        self.arg = parsed.parse_args()

    def reading(self):
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
