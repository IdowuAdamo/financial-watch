"""
Audit Hardening Test Suite: Verifier Grounding Gates, Citation Validation,
Auth & Rate Limiting, Pre-LLM PII Sanitization, and SSE Client Disconnection.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.agents.citation_validator import CitationValidator
from backend.app.agents.verifier import VerificationAgent
from backend.app.core.pii import PIIRedactor
from backend.app.core.security import RateLimiter
from backend.app.llm.mock_provider import MockProvider
from backend.app.main import app
from backend.app.models.schemas import Claim, PostAnalyzeRequest

# ==============================================================================
# 1. VERIFIER CODE-ENFORCED GROUNDING GATES
# ==============================================================================

def test_verifier_downgrades_on_missing_chunk_id():
    """Gate (a): Downgrades to insufficient_evidence if no retrieved chunk ID is cited."""
    agent = VerificationAgent(llm=MockProvider(), store=None)
    judgment = {
        "verdict": "contradicted",
        "confidence": 0.95,
        "reasoning": "This is completely false.",
        "cited_chunk_ids": ["non_existent_chunk_999"],
        "quoted_spans": ["Some quote"]
    }
    retrieved_chunks = [
        {"id": "chunk_valid_001", "content": "Official statement.", "institution_tags": []}
    ]
    claims = [Claim(claim_id="c1", topic="solvency", claim_text="Apex Horizon is bankrupt", entity="Apex Horizon Example Bank", claim_type="rumour")]
    
    verdict, conf, reason, citations, quotes, abstention_reason = agent._enforce_grounding_guardrails(
        judgment, retrieved_chunks, claims, target_bank="Apex Horizon Example Bank"
    )
    assert verdict == "insufficient_evidence"
    assert conf <= 0.35
    assert "failed to cite any chunk" in reason.lower()
    assert abstention_reason is not None

def test_verifier_downgrades_on_unverified_quote_span():
    """Gate (b): Drops citation if quoted span is not an exact substring of the cited chunk."""
    agent = VerificationAgent(llm=MockProvider(), store=None)
    chunk_text = "Apex Horizon Example Bank maintains a capital adequacy ratio of 18.5 percent."
    judgment = {
        "verdict": "supported",
        "confidence": 0.90,
        "reasoning": "Passage confirms solvency.",
        "cited_chunk_ids": ["chunk_01"],
        "quoted_spans": ["Fabricated quote that never appears in the text."]
    }
    retrieved_chunks = [
        {
            "id": "chunk_01",
            "content": chunk_text,
            "url": "https://official.apex.ng/q3",
            "source": "Apex Horizon",
            "tier": 2,
            "is_simulated": True,
            "score": 0.85,
            "institution_tags": ["Apex Horizon Example Bank"]
        }
    ]
    claims = [Claim(claim_id="c1", topic="solvency", claim_text="Apex Horizon is solvent", entity="Apex Horizon Example Bank", claim_type="rumour")]
    
    verdict, conf, reason, citations, quotes, abstention_reason = agent._enforce_grounding_guardrails(
        judgment, retrieved_chunks, claims, target_bank="Apex Horizon Example Bank"
    )
    # The citation should be dropped because the quote is not a substring
    assert verdict == "insufficient_evidence"
    assert len(citations) == 0

def test_verifier_downgrades_on_bank_mismatch():
    """Gate (d): For bank-specific claims, cited chunk must match the claim's alias-resolved bank."""
    agent = VerificationAgent(llm=MockProvider(), store=None)
    chunk_text = "Meridian Mock Bank announces scheduled maintenance on core servers."
    judgment = {
        "verdict": "contradicted",
        "confidence": 0.88,
        "reasoning": "Direct evidence of service maintenance.",
        "cited_chunk_ids": ["chunk_meridian_01"],
        "quoted_spans": ["Meridian Mock Bank announces scheduled maintenance"]
    }
    # Retrieved chunk belongs to Meridian Mock Bank, but post is about Apex Horizon Example Bank!
    retrieved_chunks = [
        {
            "id": "chunk_meridian_01",
            "content": chunk_text,
            "url": "https://meridian.ng/news",
            "source": "Meridian Mock Bank",
            "tier": 2,
            "is_simulated": True,
            "score": 0.80,
            "institution_tags": ["Meridian Mock Bank"]
        }
    ]
    claims = [Claim(claim_id="c1", topic="outage", claim_text="Apex Horizon servers are down", entity="Apex Horizon Example Bank", claim_type="rumour")]
    
    verdict, conf, reason, citations, quotes, abstention_reason = agent._enforce_grounding_guardrails(
        judgment, retrieved_chunks, claims, target_bank="Apex Horizon Example Bank"
    )
    assert verdict == "insufficient_evidence"
    assert "bank-specific claim targets" in reason.lower()
    assert len(citations) == 0

def test_verifier_capping_on_title_only_evidence():
    """Rule: Title-only evidence caps confidence at 0.65 and must directly state claim."""
    agent = VerificationAgent(llm=MockProvider(), store=None)
    title_text = "[TITLE-ONLY EVIDENCE] Official Central Bank of Nigeria Regulatory Document: CBN Revokes the Banking Licence of Heritage Bank Plc."
    judgment = {
        "verdict": "supported",
        "confidence": 0.95,
        "reasoning": "Circular title confirms revocation.",
        "cited_chunk_ids": ["chunk_title_01"],
        "quoted_spans": ["CBN Revokes the Banking Licence of Heritage Bank Plc."]
    }
    retrieved_chunks = [
        {
            "id": "chunk_title_01",
            "content": title_text,
            "url": "https://www.cbn.gov.ng/press/heritage",
            "source": "CBN",
            "tier": 1,
            "is_simulated": False,
            "is_title_only": True,
            "score": 0.92,
            "institution_tags": ["Heritage Bank"]
        }
    ]
    claims = [Claim(claim_id="c1", topic="revocation", claim_text="Heritage Bank license revoked", entity="Heritage Bank", claim_type="regulatory_action")]
    
    verdict, conf, reason, citations, quotes, abstention_reason = agent._enforce_grounding_guardrails(
        judgment, retrieved_chunks, claims, target_bank="Heritage Bank"
    )
    assert verdict == "supported"
    assert conf <= 0.65 # Title-only confidence is strictly capped
    assert citations[0].is_title_only is True

# ==============================================================================
# 2. CITATION VALIDATOR TESTS
# ==============================================================================

def test_citation_validator_valid_and_invalid_paths():
    """Validates presence and exact substring constraints."""
    retrieved = [
        {
            "id": "chunk_100",
            "content": "Deposit insurance coverage limit has been elevated to N5,000,000 by NDIC.",
            "url": "https://ndic.gov.ng/coverage"
        }
    ]
    # 1. Valid citation matching exact chunk text
    valid_text = "Official NDIC documents note: 'Deposit insurance coverage limit has been elevated to N5,000,000'."
    passed, note = CitationValidator.validate(valid_text, ["chunk_100"], retrieved)
    assert passed is True

    # 2. Invalid citation: references non-retrieved ID
    passed, note = CitationValidator.validate(valid_text, ["chunk_999"], retrieved)
    assert passed is False
    assert "does not exist in the retrieved" in note

    # 3. Invalid citation: empty cited chunk IDs
    passed, note = CitationValidator.validate(valid_text, [], retrieved)
    assert passed is False
    assert "factual statements without citing" in note

# ==============================================================================
# 3. AUTH & RATE LIMITING TESTS
# ==============================================================================

def test_rate_limiter_enforces_30_per_minute_and_retry_after():
    """Verifies that RateLimiter rejects the 31st request within a 60s window."""
    limiter = RateLimiter(max_requests_per_minute=30)
    key = "test-client-ip-127.0.0.1"

    # Send 30 allowed requests
    for _ in range(30):
        limited, retry_after = limiter.is_rate_limited(key)
        assert limited is False
        assert retry_after == 0

    # 31st request must be rate-limited
    limited, retry_after = limiter.is_rate_limited(key)
    assert limited is True
    assert retry_after > 0
    assert retry_after <= 60

@pytest.mark.asyncio
async def test_api_rate_limit_429_response():
    """Integration test: API returns 429 and Retry-After when rate limit is exceeded."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a dedicated limiter instance with 2 max requests for rapid testing
        from backend.app.core import security
        original_limiter = security.rate_limiter
        security.rate_limiter = RateLimiter(max_requests_per_minute=2)
        
        try:
            headers = {"X-API-Key": "fw-test-access-key-2026"}
            # Request 1: OK
            r1 = await client.get("/api/posts", headers=headers)
            assert r1.status_code == 200
            
            # Request 2: OK
            r2 = await client.get("/api/posts", headers=headers)
            assert r2.status_code == 200
            
            # Request 3: HTTP 429 Too Many Requests
            r3 = await client.get("/api/posts", headers=headers)
            assert r3.status_code == 429
            assert "Retry-After" in r3.headers
            assert "Rate limit exceeded" in r3.json()["detail"]
        finally:
            security.rate_limiter = original_limiter

# ==============================================================================
# 4. PRE-LLM PII SANITIZATION TESTS
# ==============================================================================

def test_pii_redacted_before_pipeline_execution():
    """Ensures Nigerian phone numbers and BVNs are sanitized before LLM ingestion."""
    raw_text = "Customer with phone 08031234567 and BVN 22345678901 reported uncredited transfer."
    redacted, stats = PIIRedactor.redact(raw_text)
    
    assert "08031234567" not in redacted
    assert "22345678901" not in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_BVN]" in redacted
    assert stats["phone_count"] == 1
    assert stats["bvn_count"] == 1

# ==============================================================================
# 5. SSE CLIENT DISCONNECT HANDLING
# ==============================================================================

@pytest.mark.asyncio
async def test_sse_disconnect_terminates_stream_cleanly():
    """Ensures that analyze_post_stream terminates early when client disconnects."""
    from backend.app.api.posts import analyze_post_stream
    
    # Mock Request with is_disconnected returning True immediately
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=True)
    
    req_payload = PostAnalyzeRequest(
        text="Apex Horizon Example Bank branch is closed today.",
        platform="Paste Intake",
        source_adapter="PasteAdapter"
    )
    
    response = await analyze_post_stream(
        req=req_payload,
        request=mock_request,
        api_key="fw-test-access-key-2026"
    )
    
    # Collect streamed chunks from the generator
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
        if len(chunks) > 5:
            break
            
    # Generator terminates early because is_disconnected is True
    assert len(chunks) <= 2
