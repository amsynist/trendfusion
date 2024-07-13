from dataclasses import dataclass

from groq import AsyncGroq

from .base_llm import BaseLLM


@dataclass
class GroqLLM(BaseLLM):

    def __post_init__(self):
        self.client = AsyncGroq(api_key=self.api_key)

    async def query(self, user_message: str) -> str | None:

        chat_completion = await self.client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            model=self.model,
        )
        return chat_completion.choices[0].message.content
