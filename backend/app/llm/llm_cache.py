"""
In-memory and persistent disk cache for LLM calls.
Prevents duplicate API calls for identical inputs and accelerates pipeline executions.
"""
import hashlib
import json
import logging
import os
from typing import Any

logger = logging.getLogger("financial_watch.llm.cache")

class LLMCache:
    """
    Key-value cache keyed by SHA-256 hash of messages and generation parameters.
    """
    def __init__(self, cache_file: str | None = None):
        self._memory_cache: dict[str, str] = {}
        self.cache_file = cache_file

        if self.cache_file and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._memory_cache = json.load(f)
                logger.info(f"Loaded {len(self._memory_cache)} cached LLM responses from {self.cache_file}")
            except Exception as e:
                logger.warning(f"Could not load LLM cache from {self.cache_file}: {e}")

    @staticmethod
    def _make_key(
        messages: Any,
        model: str,
        temperature: float,
        provider: str = "openai",
        prompt_version: str = "v2.0",
    ) -> str:
        payload = {
            "provider": provider,
            "model": model,
            "prompt_version": prompt_version,
            "temperature": round(temperature, 2),
            "messages": messages,
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(
        self,
        messages: Any,
        model: str,
        temperature: float = 0.0,
        provider: str = "openai",
        prompt_version: str = "v2.0",
    ) -> str | None:
        key = self._make_key(messages, model, temperature, provider=provider, prompt_version=prompt_version)
        val = self._memory_cache.get(key)
        if val is not None:
            logger.debug(f"LLM cache HIT for key {key[:8]}...")
        return val

    def set(
        self,
        messages: Any,
        model: str,
        temperature: float,
        response: str,
        provider: str = "openai",
        prompt_version: str = "v2.0",
    ):
        key = self._make_key(messages, model, temperature, provider=provider, prompt_version=prompt_version)
        self._memory_cache[key] = response
        if self.cache_file:
            try:
                os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self._memory_cache, f)
            except Exception as e:
                logger.warning(f"Failed to persist LLM cache: {e}")
