from abc import ABC
from dataclasses import dataclass


@dataclass
class BaseLLM(ABC):
    system_prompt: str
    model: str

    def query(self, user_message: str): ...
