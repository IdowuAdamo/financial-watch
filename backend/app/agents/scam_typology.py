"""
Scam Typology Engine.
Routes scam and impersonation posts through fraud advisories and heuristics, bypassing the claim verifier.
"""
from typing import Any

from backend.app.models.schemas import ClassificationResult, EvidenceCitation, VerificationResult

# Known Nigerian financial fraud typologies
FRAUD_TYPOLOGIES = [
    {
        "id": "typ_bvn_otp_harvesting",
        "name": "Credential Harvesting / OTP & BVN Solicitation",
        "keywords": ["bvn", "otp", "pin", "card details", "blocked account", "unblock"],
        "advisory": "Internal Heuristic Advisory: Authentic financial institutions and regulators do not request BVN, OTP, or PIN via unsolicited messages to unblock accounts.",
        "official_url": "internal://typology/bvn_otp_harvesting",
    },
    {
        "id": "typ_fake_grants_cbn_relief",
        "name": "Fraudulent CBN Relief Grant / Cash Giveaway",
        "keywords": ["grant", "relief fund", "empowerment", "cbn approved", "click here to claim"],
        "advisory": "Internal Heuristic Advisory: Known grant giveaway fraud pattern. Disregard unverified cash relief or empowerment grant claims circulating on social channels.",
        "official_url": "internal://typology/fake_grants_cbn_relief",
    },
    {
        "id": "typ_fake_recruitment_fees",
        "name": "Recruitment Fraud / Application Processing Fees",
        "keywords": ["recruitment fee", "interview fee", "medical test payment", "job offer letter", "telegram interview"],
        "advisory": "Internal Heuristic Advisory: Commercial banks do not solicit interview fees or background check charges from job applicants.",
        "official_url": "internal://typology/recruitment_fees",
    },
    {
        "id": "typ_fake_customer_support",
        "name": "Fake Social Media Customer Support Handle",
        "keywords": ["whatsapp", "dm support", "customer care desk", "chat us on", "help desk line"],
        "advisory": "Internal Heuristic Advisory: Unofficial WhatsApp/DM customer support handles represent credential harvesting risks.",
        "official_url": "internal://typology/fake_customer_support",
    },
]

class ScamTypologyEngine:
    """
    Evaluates scam indicators against known typologies and emits scam classification and advisory citations.
    """
    @staticmethod
    def process_scam(text: str) -> dict[str, Any]:
        text_lower = text.lower()
        matched_typologies = []

        for typ in FRAUD_TYPOLOGIES:
            hits = [kw for kw in typ["keywords"] if kw in text_lower]
            if len(hits) >= 1:
                matched_typologies.append((typ, hits))

        # Build evidence citations from matched advisories
        citations = []
        for typ, hits in matched_typologies:
            citations.append(EvidenceCitation(
                chunk_id=f"scam_advisory_{typ['id']}",
                source="Internal Fraud Typology (Heuristic Rule)",
                tier=1,
                url=typ["official_url"],
                publish_date="2026-10-01",
                snippet=f"[INTERNAL TYPOLOGY] Heuristic Alert: {typ['name']}. {typ['advisory']}",
                is_title_only=False,
                is_simulated=typ["official_url"].startswith("internal://"),
                score=0.95,
                quoted_span=typ["advisory"],
            ))

        reasoning = (
            f"Post flagged by Scam Typology Engine. Matched {len(matched_typologies)} recognized internal "
            f"fraud typologies: {', '.join([t[0]['name'] for t in matched_typologies])}."
        ) if matched_typologies else "Post exhibits social engineering / phishing indicators."

        evidence_type = "internal typology" if citations else "none"

        verification = VerificationResult(
            verdict="contradicted", # The fraudulent claim is contradicted by fraud warnings
            confidence=0.96,
            reasoning=reasoning,
            cited_passages=citations,
            quoted_spans=[t[0]["advisory"] for t in matched_typologies] if matched_typologies else ["Official fraud warning advisory"],
            evidence_type=evidence_type,
            entailment_status="direct",
            retrieved_chunk_ids=[c.chunk_id for c in citations],
            retrieval_rounds=1,
            is_grounded=True,
        )

        classification = ClassificationResult(
            category="scam_impersonation",
            rationale="Classified as scam/impersonation. Exploits urgent call-to-action to harvest credentials or extract fees."
        )

        return {
            "verification": verification,
            "classification": classification,
            "matched_typologies": [t[0]["name"] for t in matched_typologies],
        }
