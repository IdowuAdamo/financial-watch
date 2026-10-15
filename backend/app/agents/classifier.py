"""
Classification Agent.
Assigns risk categories {credible, unverified, misinformation, scam_impersonation}
based on verification verdicts and semantic analysis.
"""
import logging

from backend.app.llm.base import LLMProvider
from backend.app.models.schemas import ClassificationResult, TriageResult, VerificationResult

logger = logging.getLogger("financial_watch.agents.classifier")

class ClassificationAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def run(
        self,
        text: str,
        triage: TriageResult,
        verification: VerificationResult
    ) -> ClassificationResult:
        # Direct deterministic rules first
        if triage.post_type == "scam_phishing":
            return ClassificationResult(
                category="scam_impersonation",
                rationale="Flagged as fraudulent impersonation or credential harvesting scheme."
            )

        if verification.verdict == "contradicted":
            return ClassificationResult(
                category="misinformation",
                rationale=f"Core claims are contradicted by authoritative evidence: {verification.reasoning}"
            )

        if verification.verdict == "supported":
            return ClassificationResult(
                category="credible",
                rationale=f"Claims are substantiated by official regulatory/bank disclosures: {verification.reasoning}"
            )

        # For insufficient_evidence or unverifiable
        return ClassificationResult(
            category="unverified",
            rationale="Insufficient evidence in authoritative knowledge base to confirm or refute claims."
        )
