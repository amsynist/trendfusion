from ..constants import GROQ_API_KEY
from .base_llm import BaseLLM
from .groq_llm import GroqLLM


async def get_groq_llm() -> BaseLLM:
    return GroqLLM(
        model="llama3-8b-8192",
        api_key=GROQ_API_KEY,
    )
