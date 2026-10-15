"""
Abstract base class for LLM Providers.
Defines provider-agnostic interface for chat completion and vector embeddings.
"""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """
    Standard interface for LLM operations across OpenAI, Amazon Bedrock, and Mock providers.
    """
    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1000,
        response_format: dict[str, str] | None = None,
    ) -> str:
        """Generates a text completion given a list of chat messages."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generates 1536-dimensional vector embeddings for a list of strings."""

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """Generates an embedding vector for a single query string."""
