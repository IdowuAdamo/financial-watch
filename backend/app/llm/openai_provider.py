"""
OpenAI LLM Provider implementation using gpt-4o-mini and text-embedding-3-small.
Integrates with LLMCache and honors configurable model parameters from environment variables.
"""
import logging
import os
from typing import Any

import httpx
from openai import AsyncOpenAI

from backend.app.llm.base import LLMProvider
from backend.app.llm.llm_cache import LLMCache

logger = logging.getLogger("financial_watch.llm.openai")

class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        chat_model: str | None = None,
        embedding_model: str | None = None,
        cache: LLMCache | None = None,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.chat_model = chat_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.embedding_model = embedding_model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.cache = cache or LLMCache()
        
        self.client = None
        if self.api_key and not self.api_key.startswith("mock-"):
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                timeout=httpx.Timeout(60.0, connect=30.0)
            )

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1000,
        response_format: dict[str, str] | None = None,
    ) -> str:
        # Check cache first
        cached = self.cache.get(messages, self.chat_model, temperature, provider="openai", prompt_version="v2.0")
        if cached is not None:
            return cached

        if not self.client:
            raise RuntimeError("OpenAI API key not configured or in mock mode. Use MockProvider for offline execution.")

        kwargs: dict[str, Any] = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        resp = await self.client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content or ""
        
        # Save to cache
        self.cache.set(messages, self.chat_model, temperature, content, provider="openai", prompt_version="v2.0")
        return content

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.client:
            raise RuntimeError("OpenAI client not configured.")

        resp = await self.client.embeddings.create(
            model=self.embedding_model,
            input=texts,
            dimensions=1536
        )
        return [item.embedding for item in resp.data]

    async def embed_query(self, query: str) -> list[float]:
        res = await self.embed_texts([query])
        return res[0]
