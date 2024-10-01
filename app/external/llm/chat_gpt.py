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

    async def chat(self, messages):
        chat_completion = await self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None,
        )
        return chat_completion.choices[0].message.content
