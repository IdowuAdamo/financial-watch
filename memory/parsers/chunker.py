"""
Semantic text chunker with entity tagging, metadata attachment, and injection defense.
"""
import re
from typing import Any

# Prompt injection patterns to neutralize in ingested documents (anti-document poisoning)
INJECTION_NEUTRALIZE_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?previous\s+instructions",
    r"(?i)system\s+prompt",
    r"(?i)you\s+are\s+now\s+in\s+developer\s+mode",
    r"(?i)bypass\s+all\s+guidelines",
    r"(?i)output\s+the\s+secret\s+key",
]

class DocumentChunker:
    """
    Splits documents into overlapping chunks with metadata and entity tagging.
    """
    def __init__(
        self,
        target_chunk_words: int = 250,
        overlap_words: int = 40,
        known_entities: list[str] | None = None
    ):
        self.target_chunk_words = target_chunk_words
        self.overlap_words = overlap_words
        self.known_entities = known_entities or []

    @staticmethod
    def sanitize_untrusted_content(text: str) -> str:
        """
        Neutralizes prompt injection or control characters in retrieved / ingested text.
        """
        cleaned = text
        for pattern in INJECTION_NEUTRALIZE_PATTERNS:
            cleaned = re.sub(pattern, "[DISARMED_INSTRUCTION]", cleaned)
        # Strip zero-width and unprintable control characters
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)
        return cleaned

    def extract_institution_tags(self, text: str) -> list[str]:
        """
        Identifies any known bank or regulatory institutions mentioned in the chunk text.
        """
        tags = set()
        text_lower = text.lower()
        for entity in self.known_entities:
            if entity.lower() in text_lower:
                tags.add(entity)
        return sorted(list(tags))

    def chunk_document(
        self,
        doc_id: str,
        text: str,
        source: str,
        tier: int,
        url: str,
        publish_date: str | None = None,
        is_simulated: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Splits a document text into structured chunks.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        words = []
        for p in paragraphs:
            p_words = p.split()
            words.extend(p_words)

        if not words:
            return []

        chunks: list[dict[str, Any]] = []
        start_idx = 0
        chunk_idx = 0

        step = max(1, self.target_chunk_words - self.overlap_words)

        while start_idx < len(words):
            end_idx = min(start_idx + self.target_chunk_words, len(words))
            chunk_word_list = words[start_idx:end_idx]
            raw_chunk_text = " ".join(chunk_word_list)
            
            cleaned_text = self.sanitize_untrusted_content(raw_chunk_text)
            tags = self.extract_institution_tags(raw_chunk_text)

            chunk_id = f"{doc_id}_c{chunk_idx:03d}"
            chunks.append({
                "id": chunk_id,
                "document_id": doc_id,
                "chunk_index": chunk_idx,
                "content": raw_chunk_text,
                "cleaned_content": cleaned_text,
                "token_count": len(chunk_word_list),
                "tier": tier,
                "source": source,
                "url": url,
                "publish_date": publish_date or "",
                "is_simulated": is_simulated,
                "institution_tags": tags,
            })

            chunk_idx += 1
            start_idx += step

            if end_idx >= len(words):
                break

        return chunks
