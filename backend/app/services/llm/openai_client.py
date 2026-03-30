"""
OpenAI Client Wrapper — async singleton for all LLM and embedding calls.
"""

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            if not settings.openai_api_key:
                logger.warning("openai.client: OPENAI_API_KEY is not set")
            self._client = AsyncOpenAI(api_key=settings.openai_api_key or "placeholder")
        return self._client

    async def chat_complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """
        Send a chat completion request.

        Returns the assistant message content string.
        """
        selected_model = model or settings.openai_model
        logger.debug("openai.chat", extra={"model": selected_model, "turns": len(messages)})

        response = await self.client.chat.completions.create(
            model=selected_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        response = await self.client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]


openai_client = OpenAIClient()
