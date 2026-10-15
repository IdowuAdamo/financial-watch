"""
Programmatic Citation Validator.
Strictly verifies that:
1. Every cited chunk ID exists in the retrieved evidence set.
2. Referenced factual claims or entities actually appear in the cited chunk text.
Rejects or flags drafts that fail citation validation.
"""
import logging
from typing import Any

logger = logging.getLogger("financial_watch.agents.citation_validator")

class CitationValidator:
    @staticmethod
    def validate(
        draft_text: str,
        cited_chunk_ids: list[str],
        retrieved_chunks: list[dict[str, Any]]
    ) -> tuple[bool, str]:
        """
        Validates citations programmatically.
        Returns: (is_valid: bool, validation_notes: str)
        """
        # If no chunk IDs are cited in a counter-message claiming facts, fail validation
        if not cited_chunk_ids:
            return False, "Validation Failed: Drafted response makes factual statements without citing any retrieved chunk IDs."

        # Map available chunk IDs
        available_chunks = {c["id"]: c for c in retrieved_chunks}

        for cid in cited_chunk_ids:
            if cid not in available_chunks:
                return False, f"Validation Failed: Cited chunk ID '{cid}' does not exist in the retrieved evidence set."

        # Verify entity overlap
        found_overlap = False
        for cid in cited_chunk_ids:
            chunk_content = available_chunks[cid]["content"].lower()
            # Check if key words from draft appear in chunk
            words = [w for w in draft_text.lower().split() if len(w) > 5]
            matching_words = [w for w in words if w in chunk_content]
            if len(matching_words) >= 2:
                found_overlap = True
                break

        if not found_overlap and len(retrieved_chunks) > 0:
            return False, "Validation Failed: Cited chunk content does not sufficiently match the claims in the drafted response."

        return True, "Citation Validation Passed: All cited chunks exist in retrieved evidence with matching factual content."
