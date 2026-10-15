"""
Pydantic v2 schemas for all multi-agent contracts, API requests, and streaming traces.
"""
from typing import Any, Literal

from pydantic import BaseModel, Field


class PostAnalyzeRequest(BaseModel):
    text: str = Field(..., max_length=2000, description="Raw social post or claim text to analyze")
    platform: str | None = Field("Paste Form", description="Origin platform: Paste, WhatsApp, X, Facebook, etc.")
    timestamp: str | None = Field(None, description="ISO timestamp if available from post metadata")
    likes: int | None = Field(None, ge=0, description="Observed likes count if available")
    shares: int | None = Field(None, ge=0, description="Observed shares/retweets count if available")
    source_adapter: str | None = Field("PasteAdapter", description="Intake adapter identifier")

class TriageResult(BaseModel):
    post_type: Literal["reputational_rumour", "scam_phishing", "benign_feedback"]
    requires_deep_verification: bool
    urgency_level: Literal["low", "medium", "high", "critical"]
    reasoning: str

class Claim(BaseModel):
    claim_id: str
    claim_text: str
    entity: str
    topic: str

class EvidenceCitation(BaseModel):
    chunk_id: str
    source: str
    tier: int
    url: str
    publish_date: str | None = None
    snippet: str
    is_title_only: bool = False
    is_simulated: bool = False
    score: float = 0.0
    quoted_span: str | None = None

class VerificationResult(BaseModel):
    verdict: Literal["supported", "contradicted", "unverifiable", "insufficient_evidence"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    cited_passages: list[EvidenceCitation] = []
    quoted_spans: list[str] = []
    evidence_type: Literal["real", "simulated", "title-only", "internal typology", "none"] = "none"
    entailment_status: Literal["direct", "indirect", "none"] | None = None
    retrieved_chunk_ids: list[str] = []
    retrieval_rounds: int = 1
    is_grounded: bool = False
    abstention_reason: str | None = None

class ClassificationResult(BaseModel):
    category: Literal["misinformation", "scam_impersonation", "credible", "unverified"]
    rationale: str

class RiskScore(BaseModel):
    total_score: int = Field(..., ge=0, le=100)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    severity_score: float
    velocity_score: float
    reach_score: float
    verdict_score: float
    active_components: list[str]
    renormalised_note: str

class DraftedResponse(BaseModel):
    formal_response: str
    pidgin_response: str | None = None
    cited_chunk_ids: list[str] = []
    citation_validation_passed: bool = True
    validation_notes: str = "Passed"

class PipelineTraceStep(BaseModel):
    step_number: int
    agent_name: str
    status: Literal["running", "completed", "bypassed", "failed"]
    timestamp: str
    output_summary: str
    details: dict[str, Any] = {}

class FullAnalysisResult(BaseModel):
    post_id: str
    raw_text: str
    redacted_text: str
    normalized_query: str
    has_pidgin: bool
    triage: TriageResult
    claims: list[Claim] = []
    verification: VerificationResult
    classification: ClassificationResult
    risk: RiskScore
    response_draft: DraftedResponse
    approval_status: Literal["pending", "approved", "rejected", "edited"] = "pending"
    traces: list[PipelineTraceStep] = []
    created_at: str
