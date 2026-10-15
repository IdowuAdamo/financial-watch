"""
Multi-Agent Orchestration Pipeline.
Coordinates all 8 agents from intake to human-in-the-loop staging.
Streams real-time execution steps and heartbeat events over Server-Sent Events (SSE).
"""
import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from backend.app.agents.claim_extractor import ClaimExtractionAgent
from backend.app.agents.classifier import ClassificationAgent
from backend.app.agents.narrative import NarrativeAgent
from backend.app.agents.response import ResponseAgent
from backend.app.agents.risk import RiskAgent
from backend.app.agents.scam_typology import ScamTypologyEngine
from backend.app.agents.triage import TriageGateAgent
from backend.app.agents.verifier import VerificationAgent
from backend.app.core.guardrails import PromptInjectionDefense
from backend.app.core.pidgin_normalizer import PidginNormalizer
from backend.app.core.pii import PIIRedactor
from backend.app.llm.base import LLMProvider
from backend.app.models.schemas import (
    Claim,
    FullAnalysisResult,
    PipelineTraceStep,
    PostAnalyzeRequest,
)
from memory.store.db import KnowledgeBaseStore


class AnalysisPipeline:
    def __init__(
        self,
        llm: LLMProvider,
        store: KnowledgeBaseStore | None = None,
    ):
        self.llm = llm
        self.store = store or KnowledgeBaseStore()
        self.triage_agent = TriageGateAgent(llm)
        self.claim_agent = ClaimExtractionAgent(llm)
        self.verifier_agent = VerificationAgent(llm, self.store)
        self.classifier_agent = ClassificationAgent(llm)
        self.response_agent = ResponseAgent(llm)

    async def execute_stream(self, req: PostAnalyzeRequest) -> AsyncGenerator[str, None]:
        """
        Executes the 8-agent pipeline and yields formatted SSE event strings.
        Includes heartbeat pings to maintain persistent connection through CDNs and proxies.
        """
        post_id = f"post_{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(UTC).isoformat()
        traces = []

        def emit_event(event_type: str, data: dict[str, Any]) -> str:
            payload = json.dumps(data)
            return f"event: {event_type}\ndata: {payload}\n\n"

        # Emit initial start event
        yield emit_event("pipeline_start", {
            "post_id": post_id,
            "created_at": created_at,
            "platform": req.platform,
            "source_adapter": req.source_adapter,
        })
        await asyncio.sleep(0.05)

        # 1. INTAKE & PII REDACTION
        step1 = PipelineTraceStep(
            step_number=1,
            agent_name="Monitor & PII Sanitizer",
            status="running",
            timestamp=datetime.now(UTC).isoformat(),
            output_summary="Sanitizing personal identifiers and telecom prefixes.",
        )
        yield emit_event("agent_trace", step1.model_dump())

        redacted_text, pii_stats = PIIRedactor.redact(req.text)
        is_suspicious, injection_patterns = PromptInjectionDefense.inspect(redacted_text)
        guarded_text = PromptInjectionDefense.wrap_untrusted(redacted_text, "post")

        step1.status = "completed"
        step1.output_summary = f"Redacted PII (Phones: {pii_stats['phone_count']}, BVN: {pii_stats['bvn_count']}). Injections: {len(injection_patterns)}."
        step1.details = {"pii_stats": pii_stats, "injection_flag": is_suspicious}
        traces.append(step1)
        yield emit_event("agent_trace", step1.model_dump())
        await asyncio.sleep(0.05)

        # Heartbeat ping
        yield emit_event("ping", {"timestamp": datetime.now(UTC).isoformat()})

        # 2. PIDGIN NORMALIZATION & ENTITY RESOLUTION
        step2 = PipelineTraceStep(
            step_number=2,
            agent_name="Pidgin Normalizer & Entity Resolver",
            status="running",
            timestamp=datetime.now(UTC).isoformat(),
            output_summary="Translating colloquial Pidgin vernacular into normalized search tokens.",
        )
        yield emit_event("agent_trace", step2.model_dump())

        normalized_query, has_pidgin = PidginNormalizer.normalize(redacted_text)

        step2.status = "completed"
        step2.output_summary = f"Pidgin Detected: {has_pidgin}. Normalized search query ready."
        step2.details = {"has_pidgin": has_pidgin, "normalized_query": normalized_query}
        traces.append(step2)
        yield emit_event("agent_trace", step2.model_dump())
        await asyncio.sleep(0.05)

        # 3. TRIAGE GATE
        step3 = PipelineTraceStep(
            step_number=3,
            agent_name="Triage Gate Agent",
            status="running",
            timestamp=datetime.now(UTC).isoformat(),
            output_summary="Pre-screening for scam typologies vs banking reputational claims.",
        )
        yield emit_event("agent_trace", step3.model_dump())

        triage = await self.triage_agent.run(normalized_query)

        step3.status = "completed"
        step3.output_summary = f"Type: {triage.post_type} | Urgency: {triage.urgency_level} | Deep Verification: {triage.requires_deep_verification}"
        step3.details = triage.model_dump()
        traces.append(step3)
        yield emit_event("agent_trace", step3.model_dump())
        await asyncio.sleep(0.05)

        # Heartbeat ping
        yield emit_event("ping", {"timestamp": datetime.now(UTC).isoformat()})

        # 4. ROUTING: SCAM BYPASS vs CLAIM EXTRACTION & VERIFICATION
        claims: List[Claim] = []
        retrieved_raw_chunks: list = []

        if triage.post_type == "scam_phishing":
            # SCAM TYPOLOGY ENGINE BYPASS
            step4 = PipelineTraceStep(
                step_number=4,
                agent_name="Scam Typology Engine (Bypass)",
                status="completed",
                timestamp=datetime.now(UTC).isoformat(),
                output_summary="Bypassed claim verifier; routed to fraud advisory repository.",
            )
            scam_res = ScamTypologyEngine.process_scam(redacted_text)
            verification = scam_res["verification"]
            classification = scam_res["classification"]
            step4.details = {"typologies": scam_res["matched_typologies"]}
            traces.append(step4)
            yield emit_event("agent_trace", step4.model_dump())

        else:
            # 4a. CLAIM EXTRACTION
            step4a = PipelineTraceStep(
                step_number=4,
                agent_name="Claim Extraction Agent",
                status="running",
                timestamp=datetime.now(UTC).isoformat(),
                output_summary="Deconstructing post into checkable claims.",
            )
            yield emit_event("agent_trace", step4a.model_dump())

            claims = await self.claim_agent.run(normalized_query)

            step4a.status = "completed"
            step4a.output_summary = f"Extracted {len(claims)} discrete claims."
            step4a.details = {"claims": [c.model_dump() for c in claims]}
            traces.append(step4a)
            yield emit_event("agent_trace", step4a.model_dump())
            await asyncio.sleep(0.05)

            # Heartbeat ping
            yield emit_event("ping", {"timestamp": datetime.now(UTC).isoformat()})

            # 4b. BOUNDED VERIFICATION LOOP
            step4b = PipelineTraceStep(
                step_number=5,
                agent_name="Verification Agent (Bounded Loop)",
                status="running",
                timestamp=datetime.now(UTC).isoformat(),
                output_summary="Executing iterative hybrid retrieval against Tier 1/2 Knowledge Base.",
            )
            yield emit_event("agent_trace", step4b.model_dump())

            verification = await self.verifier_agent.run(claims, redacted_text, normalized_query)

            step4b.status = "completed"
            step4b.output_summary = f"Verdict: {verification.verdict} (Confidence: {int(verification.confidence * 100)}%) across {verification.retrieval_rounds} rounds."
            step4b.details = {
                "verdict": verification.verdict,
                "confidence": verification.confidence,
                "citations": [c.model_dump() for c in verification.cited_passages]
            }
            traces.append(step4b)
            yield emit_event("agent_trace", step4b.model_dump())
            await asyncio.sleep(0.05)

            # 4c. CLASSIFICATION AGENT
            step4c = PipelineTraceStep(
                step_number=6,
                agent_name="Classification Agent",
                status="running",
                timestamp=datetime.now(UTC).isoformat(),
                output_summary="Assigning risk taxonomy category.",
            )
            yield emit_event("agent_trace", step4c.model_dump())

            classification = await self.classifier_agent.run(redacted_text, triage, verification)

            step4c.status = "completed"
            step4c.output_summary = f"Category: {classification.category.upper()} | {classification.rationale[:80]}..."
            step4c.details = classification.model_dump()
            traces.append(step4c)
            yield emit_event("agent_trace", step4c.model_dump())

        # Heartbeat ping
        yield emit_event("ping", {"timestamp": datetime.now(UTC).isoformat()})

        # 5. NARRATIVE CLUSTERING
        step5 = PipelineTraceStep(
            step_number=7,
            agent_name="Narrative Clustering Agent",
            status="running",
            timestamp=datetime.now(UTC).isoformat(),
            output_summary="Mapping claim to known narrative cluster archetypes.",
        )
        yield emit_event("agent_trace", step5.model_dump())

        narrative = NarrativeAgent.cluster(redacted_text, claims)

        step5.status = "completed"
        step5.output_summary = f"Assigned to Cluster: '{narrative['cluster_title']}'"
        step5.details = narrative
        traces.append(step5)
        yield emit_event("agent_trace", step5.model_dump())
        await asyncio.sleep(0.05)

        # 6. RISK SCORING WITH WEIGHT RENORMALISATION
        step6 = PipelineTraceStep(
            step_number=8,
            agent_name="Risk Agent",
            status="running",
            timestamp=datetime.now(UTC).isoformat(),
            output_summary="Calculating mathematical 0-100 risk score and renormalising missing factors.",
        )
        yield emit_event("agent_trace", step6.model_dump())

        risk = RiskAgent.compute(
            narrative_cluster=narrative,
            verification=verification,
            classification=classification,
            likes=req.likes,
            shares=req.shares,
            timestamp=req.timestamp,
        )

        step6.status = "completed"
        step6.output_summary = f"Risk Score: {risk.total_score}/100 [{risk.risk_level}]. Active Factors: {', '.join(risk.active_components)}."
        step6.details = risk.model_dump()
        traces.append(step6)
        yield emit_event("agent_trace", step6.model_dump())
        await asyncio.sleep(0.05)

        # 7. RESPONSE DRAFTING & CITATION VALIDATION
        step7 = PipelineTraceStep(
            step_number=9,
            agent_name="Response Agent & Citation Validator",
            status="running",
            timestamp=datetime.now(UTC).isoformat(),
            output_summary="Drafting grounded counter-messages and programmatically validating citations.",
        )
        yield emit_event("agent_trace", step7.model_dump())

        # Pull raw chunk representations for validation
        raw_chunks_for_val = [
            {"id": c.chunk_id, "content": c.snippet, "url": c.url}
            for c in verification.cited_passages
        ]
        response_draft = await self.response_agent.draft(
            raw_text=redacted_text,
            verification=verification,
            classification=classification,
            retrieved_chunks=raw_chunks_for_val,
        )

        step7.status = "completed"
        step7.output_summary = f"Drafted dual-tone responses. Citation Validation: {response_draft.citation_validation_passed}."
        step7.details = response_draft.model_dump()
        traces.append(step7)
        yield emit_event("agent_trace", step7.model_dump())
        await asyncio.sleep(0.05)

        # 8. HUMAN-IN-THE-LOOP STAGING
        step8 = PipelineTraceStep(
            step_number=10,
            agent_name="Human-in-the-Loop Approval Gate",
            status="completed",
            timestamp=datetime.now(UTC).isoformat(),
            output_summary="Draft staged in approval queue. Auto-posting strictly prohibited.",
            details={"status": "pending_human_review"},
        )
        traces.append(step8)
        yield emit_event("agent_trace", step8.model_dump())

        # Compile final complete payload
        full_result = FullAnalysisResult(
            post_id=post_id,
            raw_text=req.text,
            redacted_text=redacted_text,
            normalized_query=normalized_query,
            has_pidgin=has_pidgin,
            triage=triage,
            claims=claims,
            verification=verification,
            classification=classification,
            risk=risk,
            response_draft=response_draft,
            approval_status="pending",
            traces=traces,
            created_at=created_at,
        )

        # Emit completion event with the entire payload
        yield emit_event("pipeline_complete", full_result.model_dump())
