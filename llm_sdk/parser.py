from dataclasses import field
import json
from typing import Literal
from pydantic import BaseModel


class Param(BaseModel):
    type: str


class Function(BaseModel):
    name: str
    description: str
    parameters: dict[str, Param]
    returns : Param
