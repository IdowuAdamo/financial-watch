"""
Triage Gate Agent.
Performs fast, low-cost pre-classification to separate scam/phishing posts
from reputational rumours before running expensive verification loops.
"""
import logging
import re

from backend.app.core.guardrails import parse_json_markdown
from backend.app.llm.base import LLMProvider
from backend.app.models.schemas import TriageResult

logger = logging.getLogger("financial_watch.agents.triage")

# Fast heuristic signatures for scam/phishing
SCAM_HEURISTICS = [
    r"(?i)\b(?:bvn|pin|otp|password)\b",
    r"(?i)\b(?:urgent|immediately|within\s+24\s+hours|suspended|blocked)\b",
    r"(?i)\b(?:whatsapp|telegram|dm\s+us|inbox\s+me)\b",
    r"(?i)\b(?:free\s+grant|cbn\s+relief|claim\s+your\s+fund|bonus|giveaway)\b",
    r"(?i)\b(?:interview\s+fee|processing\s+charge|recruitment\s+form)\b",
    r"(?i)https?://bit\.ly|tinyurl|is\.gd|cutt\.ly",
]

class TriageGateAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def run(self, text: str) -> TriageResult:
        """
        Quickly triages post using regex heuristics followed by cheap LLM confirmation if needed.
        """
        # 1. Fast Heuristic Check
        heuristic_matches = []
        for pat in SCAM_HEURISTICS:
            if re.search(pat, text):
                heuristic_matches.append(pat)

        # If strong scam signals detected, route directly without LLM latency
        if len(heuristic_matches) >= 2:
            return TriageResult(
                post_type="scam_phishing",
                requires_deep_verification=False,
                urgency_level="high",
                reasoning=f"Matched {len(heuristic_matches)} scam/phishing heuristic patterns (urgent call-to-action, credential harvesting, or unofficial channels)."
            )

        # 2. LLM Triage Confirmation
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a fast financial risk triage classifier. Classify the user post into either:\n"
                    "- 'scam_phishing': Impersonation, phishing, fraud, credential theft, fake grants.\n"
                    "- 'reputational_rumour': Banking distress, license revocation, solvency claims, bank runs, IT outages.\n"
                    "- 'benign_feedback': General customer service feedback or harmless chatter.\n"
                    "Output valid JSON matching: {'post_type': '...', 'requires_deep_verification': bool, 'urgency_level': 'low'|'medium'|'high'|'critical', 'reasoning': '...'}"
                )
            },
            {"role": "user", "content": f"Post text to triage:\n{text}"}
        ]

        try:
            raw = await self.llm.chat_completion(messages, temperature=0.0)
            data = parse_json_markdown(raw)
            return TriageResult(

                post_type=data.get("post_type", "reputational_rumour"),
                requires_deep_verification=data.get("requires_deep_verification", True),
                urgency_level=data.get("urgency_level", "medium"),
                reasoning=data.get("reasoning", "Classified by triage gate.")
            )
        except Exception as e:
            logger.warning(f"LLM triage fallback: {e}")
            from backend.app.llm.mock_provider import MockProvider
            if not isinstance(self.llm, MockProvider):
                raise
            return TriageResult(
                post_type="reputational_rumour",
                requires_deep_verification=True,
                urgency_level="medium",
                reasoning="Defaulted to reputational verification."
            )
