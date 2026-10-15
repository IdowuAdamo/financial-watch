"""
Claim Extraction Agent.
Deconstructs raw narrative text into discrete, checkable atomic claims.
"""
import logging

from backend.app.core.guardrails import parse_json_markdown
from backend.app.llm.base import LLMProvider
from backend.app.models.schemas import Claim

logger = logging.getLogger("financial_watch.agents.claim_extractor")

class ClaimExtractionAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def run(self, text: str) -> list[Claim]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a financial intelligence claim extraction agent. "
                    "Analyze the given text and extract discrete, checkable factual claims. "
                    "Focus strictly on: bank distress, solvency, license status, regulatory directives, "
                    "customer fund safety, and systems outages.\n"
                    "Output JSON matching: {'claims': [{'claim_id': 'c1', 'claim_text': '...', 'entity': '...', 'topic': '...'}]}"
                )
            },
            {"role": "user", "content": f"Text:\n{text}"}
        ]

        try:
            raw = await self.llm.chat_completion(messages, temperature=0.0)
            data = parse_json_markdown(raw)
            raw_claims = data.get("claims", [])

            claims = [Claim(**c) for c in raw_claims]
            if claims:
                return claims
        except Exception as e:
            logger.warning(f"LLM claim extraction fallback: {e}")
            from backend.app.llm.mock_provider import MockProvider
            if not isinstance(self.llm, MockProvider):
                raise

        # Fallback single claim
        return [
            Claim(
                claim_id="c1",
                claim_text=text[:150],
                entity="Banking Institution",
                topic="general_rumour"
            )
        ]
