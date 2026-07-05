from dataclasses import field
import json
from typing import Literal

from pydantic import BaseModel

loaded = []
try:
    with open("data/input/functions_definition.json", "r") as file:
        loaded = json.load(file)
except BaseException as e:
    print(e)

data = {}
for function in loaded:
    data[function["name"]] = function


class param(BaseModel):
    typ: str


class Function(BaseModel):
    name: str = Literal[""]
