from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BaseLLM(ABC):
    model: str
    api_key: str
    system_prompt: str = "Anwser User Queries"

    def format_system_prompt(self, **kwargs):
        self.system_prompt = self.system_prompt.format(**kwargs)

    @abstractmethod
    async def query(self, user_message: str) -> str | None:
        pass
