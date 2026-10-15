"""
Response Drafting Agent.
Generates grounded counter-messages citing verified KB chunk IDs.
Emits both a formal corporate statement and a Nigerian Pidgin community debunk.
Validates citations programmatically before submitting to the Human-in-the-Loop queue.
"""
import logging
from typing import Any

from backend.app.agents.citation_validator import CitationValidator
from backend.app.core.guardrails import parse_json_markdown
from backend.app.llm.base import LLMProvider
from backend.app.models.schemas import ClassificationResult, DraftedResponse, VerificationResult

logger = logging.getLogger("financial_watch.agents.response")

class ResponseAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def draft(
        self,
        raw_text: str,
        verification: VerificationResult,
        classification: ClassificationResult,
        retrieved_chunks: list[dict[str, Any]],
    ) -> DraftedResponse:
        # If unverified / insufficient evidence, generate standard cautious holding advisory
        if verification.verdict == "insufficient_evidence" or classification.category == "unverified":
            return DraftedResponse(
                formal_response=(
                    "Public Notice: Reports currently circulating regarding this matter have not been substantiated "
                    "by any official circular or regulatory disclosure from the Central Bank of Nigeria. "
                    "The public is advised to exercise caution and rely strictly on official communications."
                ),
                pidgin_response=(
                    "Make una hold on first! No official document from CBN or the bank confirm this gist. "
                    "Make una no spread news wey no get proof."
                ),
                cited_chunk_ids=[],
                citation_validation_passed=True,
                validation_notes="Holding statement: insufficient evidence to assert or refute.",
            )

        # Prepare evidence context
        evidence_text = "\n\n".join([
            f"[ID: {c.chunk_id}] Source: {c.source} ({c.url})\n{c.snippet}"
            for c in verification.cited_passages
        ])
        candidate_ids = [c.chunk_id for c in verification.cited_passages]

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert financial communications response officer. "
                    "Draft an authoritative, transparent public counter-message strictly grounded in the retrieved evidence.\n"
                    "RULES:\n"
                    "1. Every factual statement must cite one of the candidate chunk IDs in brackets (e.g. [chunk_id]).\n"
                    "2. Draft two versions:\n"
                    "   - 'formal_response': Professional, measured corporate statement citing official policy or statements.\n"
                    "   - 'pidgin_response': Accessible, culturally resonant Nigerian Pidgin social debunk.\n"
                    "3. For citations from 'Internal Fraud Typology' or internal typology rules, NEVER attribute their wording to the Central Bank of Nigeria (CBN) or any official regulator. Describe them strictly as internal security advisories and standard fraud warnings.\n"
                    "Output JSON: {'formal_response': '...', 'pidgin_response': '...', 'cited_chunk_ids': ['...']}"
                )
            },
            {
                "role": "user",
                "content": (
                    f"Misinformation/Rumour to address:\n{raw_text}\n\n"
                    f"Classification: {classification.category}\n"
                    f"Verification Reasoning: {verification.reasoning}\n\n"
                    f"Retrieved Authoritative Evidence:\n{evidence_text}"
                )
            }
        ]

        try:
            raw = await self.llm.chat_completion(messages, temperature=0.0)
            data = parse_json_markdown(raw)
            formal = data.get("formal_response", "")

            pidgin = data.get("pidgin_response", "")
            cited_ids = data.get("cited_chunk_ids", candidate_ids)
        except Exception as e:
            logger.warning(f"LLM response drafting fallback: {e}")
            from backend.app.llm.mock_provider import MockProvider
            if not isinstance(self.llm, MockProvider):
                raise
            formal = (
                f"Official Clarification: Statements alleging distress are inaccurate. Official regulatory records "
                f"confirm stability. Ref: {candidate_ids[0] if candidate_ids else 'Regulatory Record'}."
            )
            pidgin = "Make una no panic o! Bank dey work fine and all money dey safe."
            cited_ids = candidate_ids

        # Programmatic citation validation
        is_valid, validation_notes = CitationValidator.validate(
            draft_text=formal,
            cited_chunk_ids=cited_ids,
            retrieved_chunks=retrieved_chunks
        )

        return DraftedResponse(
            formal_response=formal,
            pidgin_response=pidgin,
            cited_chunk_ids=cited_ids,
            citation_validation_passed=is_valid,
            validation_notes=validation_notes,
        )
