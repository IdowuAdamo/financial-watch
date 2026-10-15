"""
Unit tests for multi-agent logic, bounded verifier, citation validator, and risk scoring.
"""
import pytest

from backend.app.agents.citation_validator import CitationValidator
from backend.app.agents.risk import RiskAgent
from backend.app.agents.scam_typology import ScamTypologyEngine
from backend.app.agents.triage import TriageGateAgent
from backend.app.llm.mock_provider import MockProvider
from backend.app.models.schemas import ClassificationResult, VerificationResult


@pytest.mark.asyncio
async def test_triage_detects_scam_heuristic():
    mock_llm = MockProvider()
    triage_agent = TriageGateAgent(mock_llm)
    
    scam_text = "Urgent! Send your BVN and OTP to our WhatsApp desk within 24 hours to unblock account."
    result = await triage_agent.run(scam_text)
    
    assert result.post_type == "scam_phishing"
    assert result.requires_deep_verification is False
    assert result.urgency_level == "high"

def test_scam_typology_engine_bypass():
    scam_text = "Claim your N50,000 CBN relief fund grant immediately."
    result = ScamTypologyEngine.process_scam(scam_text)
    
    assert result["classification"].category == "scam_impersonation"
    assert result["verification"].verdict == "contradicted"
    assert len(result["verification"].cited_passages) > 0

def test_citation_validator_passes_valid_chunk():
    retrieved_chunks = [
        {
            "id": "chunk_cbn_title_7472",
            "content": "Official Central Bank of Nigeria Regulatory Document: CBN Revokes the Banking Licence of Heritage Bank Plc.",
            "url": "https://www.cbn.gov.ng/Out/2024/CCD/CBN Press Release Heritage 030624.pdf"
        }
    ]
    draft_text = "Official record confirms CBN revoked the banking licence of Heritage Bank Plc."
    cited_ids = ["chunk_cbn_title_7472"]
    
    is_valid, note = CitationValidator.validate(draft_text, cited_ids, retrieved_chunks)
    assert is_valid is True
    assert "Passed" in note

def test_citation_validator_rejects_missing_chunk():
    retrieved_chunks = [
        {"id": "chunk_001", "content": "Some unrelated content."}
    ]
    draft_text = "Claims are verified by official directive."
    cited_ids = ["non_existent_chunk_id"]
    
    is_valid, note = CitationValidator.validate(draft_text, cited_ids, retrieved_chunks)
    assert is_valid is False
    assert "Validation Failed" in note

def test_risk_score_dynamic_renormalisation():
    narrative = {"base_severity": 90}
    verif = VerificationResult(verdict="contradicted", confidence=0.9, reasoning="Contradicted")
    classif = ClassificationResult(category="misinformation", rationale="Misinformation")

    # Case A: Missing engagement metadata (likes/shares missing)
    risk_no_eng = RiskAgent.compute(narrative, verif, classif, likes=None, shares=None, timestamp=None)
    assert "Reach (Engagement Metric)" not in risk_no_eng.active_components
    assert "renormalised" in risk_no_eng.renormalised_note.lower()
    assert risk_no_eng.total_score >= 80

    # Case B: Full engagement metadata provided
    risk_with_eng = RiskAgent.compute(narrative, verif, classif, likes=500, shares=200, timestamp="2026-10-14T08:00:00Z")
    assert "Reach (Engagement Metric)" in risk_with_eng.active_components
    assert "Velocity (Spread Acceleration)" in risk_with_eng.active_components
    assert "Full multi-factor" in risk_with_eng.renormalised_note
