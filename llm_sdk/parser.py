import json
from typing import List
from pydantic import BaseModel


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
        self.reading()

    def reading(self):
        try:
            with open("data/input/functions_definition.json", "r") as file:
                self.loaded = json.load(file)
        except BaseException:
            print("Error Reading the file")
        for x in self.loaded:
            if not x['name'].startswith("fn_"):
                raise ValueError
            function = Function(**x)
            self.functions.append(function)
            self.names.append(x['name'])
