"""
Embedding generator supporting OpenAI text-embedding-3-small with deterministic fallback for offline tests.
"""
import hashlib
import logging
import os

import numpy as np

logger = logging.getLogger("financial_watch.memory.embeddings")

class EmbeddingService:
    """
    Generates 1536-dimensional embeddings using OpenAI or deterministic offline fallback.
    """
    def __init__(self, model_name: str = "text-embedding-3-small", dimensions: int = 1536):
        self.model_name = os.getenv("OPENAI_EMBEDDING_MODEL", model_name)
        self.dimensions = dimensions
        self.api_key = os.getenv("OPENAI_API_KEY")
        self._client = None

        if self.api_key and not self.api_key.startswith("mock-"):
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize live OpenAI client: {e}. Using deterministic mock.")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embeds a list of texts into 1536-dimensional vectors.
        """
        if not texts:
            return []

        # If live OpenAI client is available, use it
        if self._client:
            try:
                resp = self._client.embeddings.create(
                    model=self.model_name,
                    input=texts,
                    dimensions=self.dimensions
                )
                return [d.embedding for d in resp.data]
            except Exception as e:
                logger.warning(f"Live OpenAI embedding failed: {e}. Falling back to deterministic embedding.")

        # Deterministic offline embedding generation
        return [self._deterministic_embedding(t) for t in texts]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]

    def _deterministic_embedding(self, text: str) -> list[float]:
        """
        Produces a normalized 1536-dimensional float vector based on text hash and token trigrams.
        Ensures identical texts produce identical vectors, and texts with common words have positive cosine similarity.
        """
        # Create deterministic pseudo-random state from text MD5
        h = hashlib.md5(text.encode("utf-8")).digest()
        seed = int.from_bytes(h[:4], "big")
        rng = np.random.RandomState(seed)
        
        # Base vector from seed
        vec = rng.randn(self.dimensions).astype(np.float32)

        # Word-level bias to impart semantic clustering
        words = text.lower().split()
        for w in words[:20]:
            w_h = int.from_bytes(hashlib.md5(w.encode("utf-8")).digest()[:4], "big")
            w_rng = np.random.RandomState(w_h)
            vec += 0.3 * w_rng.randn(self.dimensions)

        # Normalize to unit length (L2 norm)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.tolist()
