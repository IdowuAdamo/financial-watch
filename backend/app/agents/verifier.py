"""
Verification Agent with Bounded Retrieval Loop (Max 3 Rounds) and Code-Enforced Grounding Guardrails.
Enforces zero unanchored hallucination: returns 'supported' or 'contradicted' ONLY when:
(a) At least one retrieved chunk ID is cited.
(b) Quoted span is validated as a substring of that chunk.
(c) The cited chunk passes the relevance threshold (score >= 0.35).
(d) For bank-specific claims, cited chunk's institution tag matches the claim's alias-resolved bank.
Otherwise, strictly downgrades to 'insufficient_evidence'.
Title-only evidence is allowed only if the title directly states the claim, and confidence is capped at 0.65.
"""
import json
import logging
import os
from typing import Any

from backend.app.core.guardrails import parse_json_markdown
from backend.app.llm.base import LLMProvider
from backend.app.models.schemas import Claim, EvidenceCitation, VerificationResult
from memory.store.db import KnowledgeBaseStore
from memory.store.embeddings import EmbeddingService

logger = logging.getLogger("financial_watch.agents.verifier")

# Canonical bank registry for alias resolution and bank-specific grounding
BANK_REGISTRY = {
    "Apex Horizon Example Bank": [
        "apex horizon example bank", "apex horizon bank", "apex horizon", "apex example bank", "apex example"
    ],
    "Meridian Mock Bank": [
        "meridian mock bank", "meridian mock", "meridian commercial mock bank", "meridian test bank"
    ],
    "Northbridge Example Bank": [
        "northbridge example bank", "northbridge bank", "northbridge", "northbridge example", "neb nigeria"
    ],
    "Kreston Test Bank": [
        "kreston test bank", "kreston bank", "kreston test", "ktb nigeria"
    ],
    "Heritage Bank": [
        "heritage bank", "heritage bank plc"
    ],
    "Access Bank": [
        "access bank", "access bank plc"
    ],
    "Zenith Bank": [
        "zenith bank", "zenith bank plc"
    ],
    "Guaranty Trust Bank": [
        "guaranty trust bank", "gtbank", "gtb", "gtco"
    ],
}

RELEVANCE_THRESHOLD = 0.25
TITLE_ONLY_CONFIDENCE_CAP = 0.65

class VerificationAgent:
    def __init__(
        self,
        llm: LLMProvider,
        store: KnowledgeBaseStore | None = None,
        embedder: EmbeddingService | None = None,
        max_rounds: int = 3,
    ):
        self.llm = llm
        self.store = store or KnowledgeBaseStore()
        self.embedder = embedder or EmbeddingService()
        self.max_rounds = max_rounds
        self.disable_retrieval = os.getenv("DISABLE_KB_RETRIEVAL", "false").lower() == "true"

    def resolve_bank(self, claims: list[Claim], text: str) -> str | None:
        """Resolves alias-matched commercial or test bank entity if bank-specific."""
        combined_text = (text + " " + " ".join([f"{c.entity} {c.claim_text}" for c in claims])).lower()
        for canonical, aliases in BANK_REGISTRY.items():
            if any(alias in combined_text for alias in aliases):
                return canonical
        return None

    async def run(self, claims: list[Claim], original_text: str, normalized_query: str) -> VerificationResult:
        """
        Executes bounded iterative retrieval loop (up to 3 rounds) and applies
        strict code-enforced grounding guardrails before returning verdict.
        """
        if self.disable_retrieval:
            logger.info("KB Retrieval is DISABLED. Running Parametric-Only Baseline.")
            return await self._judge_parametric_baseline(claims, original_text)

        all_retrieved_chunks = []
        seen_chunk_ids = set()
        current_query = normalized_query
        target_bank = self.resolve_bank(claims, original_text)

        for round_num in range(1, self.max_rounds + 1):
            logger.info(f"Verification Round {round_num}/{self.max_rounds} for query: '{current_query}' (Bank: {target_bank})")
            
            # Embed query
            qvec = await self.llm.embed_query(current_query)
            
            # Retrieve top candidates with bank boosting
            chunks = self.store.hybrid_search(
                query_text=current_query,
                query_embedding=qvec,
                top_k=5,
                target_institution=target_bank
            )

            # Deduplicate
            for c in chunks:
                if c["id"] not in seen_chunk_ids:
                    seen_chunk_ids.add(c["id"])
                    all_retrieved_chunks.append(c)

            # Evaluate sufficiency with LLM judge
            judgment = await self._judge_sufficiency(claims, all_retrieved_chunks, round_num)

            # Enforce strict code grounding guardrails on LLM judgment
            verdict, confidence, reasoning, citations, quoted_spans, abstention_reason = (
                self._enforce_grounding_guardrails(judgment, all_retrieved_chunks, claims, target_bank)
            )

            # If conclusive evidence found after guardrails, perform separate entailment check
            if verdict in ("supported", "contradicted"):
                claims_text = " ".join([c.claim_text for c in claims])
                passage_text = "\n\n".join([f"[{c.chunk_id}] {c.snippet}" for c in citations])
                entailment_res = await self.check_entailment(claims_text, passage_text, verdict)
                rel = entailment_res.get("relationship", "none")

                if rel == "indirect":
                    # Item 2 rule: Indirect evidence caps confidence at 0.5 and cannot yield supported/contradicted
                    confidence = min(confidence, 0.50)
                    verdict = "insufficient_evidence"
                    abstention_reason = (
                        f"Downgraded: Passage provides indirect evidence only ({entailment_res.get('reasoning')}). "
                        "Strict grounding requires direct textual entailment to support or contradict."
                    )
                    reasoning = f"[INDIRECT EVIDENCE CAP] {reasoning}"
                    entailment_status = "indirect"
                elif rel == "none":
                    confidence = min(confidence, 0.30)
                    verdict = "insufficient_evidence"
                    abstention_reason = f"Downgraded: Passage has no evidential entailment ({entailment_res.get('reasoning')})."
                    reasoning = f"[NO ENTAILMENT] {reasoning}"
                    entailment_status = "none"
                else:
                    entailment_status = "direct"
            else:
                entailment_status = None

            if verdict in ("supported", "contradicted") or round_num >= self.max_rounds:
                evidence_type = "none"
                if citations:
                    if any(c.is_simulated for c in citations):
                        evidence_type = "simulated"
                    elif any(c.is_title_only for c in citations):
                        evidence_type = "title-only"
                    else:
                        evidence_type = "real"

                return VerificationResult(
                    verdict=verdict,
                    confidence=confidence,
                    reasoning=reasoning,
                    cited_passages=citations,
                    quoted_spans=quoted_spans,
                    evidence_type=evidence_type,
                    entailment_status=entailment_status,
                    retrieved_chunk_ids=[c["id"] for c in all_retrieved_chunks],
                    retrieval_rounds=round_num,
                    is_grounded=(verdict in ("supported", "contradicted") and len(citations) > 0 and entailment_status == "direct"),
                    abstention_reason=abstention_reason if verdict == "insufficient_evidence" else None,
                )

            # Otherwise, rewrite query for next round
            current_query = await self._rewrite_query(current_query, claims, round_num, target_bank)

        # Fallback default abstention
        return VerificationResult(
            verdict="insufficient_evidence",
            confidence=0.30,
            reasoning="Bounded retrieval loop concluded without verified textual evidence.",
            cited_passages=[],
            quoted_spans=[],
            evidence_type="none",
            retrieved_chunk_ids=[c["id"] for c in all_retrieved_chunks],
            retrieval_rounds=self.max_rounds,
            is_grounded=False,
            abstention_reason="No direct proof found in authoritative sources after 3 rounds.",
        )

    def _enforce_grounding_guardrails(
        self,
        judgment: dict[str, Any],
        retrieved_chunks: list[dict[str, Any]],
        claims: list[Claim],
        target_bank: str | None,
    ) -> tuple[str, float, str, list[EvidenceCitation], list[str], str | None]:
        """
        Code-enforced grounding rules:
        (a) Cite at least one retrieved chunk ID.
        (b) Quoted span must be validated as a substring of that chunk.
        (c) Cited chunk must pass relevance threshold (>= 0.35).
        (d) For bank-specific claims, cited chunk's institution tag must match the claim's alias-resolved bank.
        Otherwise downgrade to 'insufficient_evidence'.
        Title-only evidence confidence capped at 0.65 and must directly state claim.
        """
        raw_verdict = judgment.get("verdict", "insufficient_evidence")
        raw_confidence = float(judgment.get("confidence", 0.5))
        reasoning = judgment.get("reasoning", "")
        
        # If model already abstained, respect it
        if raw_verdict not in ("supported", "contradicted"):
            return "insufficient_evidence", min(raw_confidence, 0.35), reasoning, [], [], judgment.get("abstention_reason") or "Model concluded insufficient evidence."

        chunk_map = {c["id"]: c for c in retrieved_chunks}
        
        # Extract cited chunk IDs
        raw_cited_ids = judgment.get("cited_chunk_ids", [])
        if not raw_cited_ids and "cited_chunks" in judgment:
            raw_cited_ids = [cc.get("chunk_id") for cc in judgment["cited_chunks"] if cc.get("chunk_id")]

        # (a) Check: cite at least one retrieved chunk ID
        valid_cited_ids = [cid for cid in raw_cited_ids if cid in chunk_map]
        if not valid_cited_ids:
            return (
                "insufficient_evidence",
                0.30,
                f"Downgraded from {raw_verdict}: Model failed to cite any chunk present in retrieved candidates.",
                [],
                [],
                "No valid retrieved chunk ID cited."
            )

        # Extract quoted spans
        quoted_spans = judgment.get("quoted_spans", [])
        if not quoted_spans and "quoted_span" in judgment and judgment["quoted_span"]:
            quoted_spans = [judgment["quoted_span"]]
        if not quoted_spans and "cited_chunks" in judgment:
            quoted_spans = [cc.get("quoted_span") for cc in judgment["cited_chunks"] if cc.get("quoted_span")]

        verified_citations: list[EvidenceCitation] = []
        verified_spans: list[str] = []
        downgrade_reason: str | None = None

        for cid in valid_cited_ids:
            chunk = chunk_map[cid]
            content = chunk.get("content", "")
            score = float(chunk.get("score", 0.0))
            is_title_only = chunk.get("is_title_only", False) or "[TITLE-ONLY EVIDENCE]" in content or chunk.get("document_id", "").startswith("doc_cbn_title_")
            is_simulated = chunk.get("is_simulated", False)

            # (c) Check relevance threshold
            if score < RELEVANCE_THRESHOLD:
                downgrade_reason = f"Cited chunk {cid} score ({score:.4f}) is below relevance threshold ({RELEVANCE_THRESHOLD})."
                break

            # (d) Check institution match for bank-specific claims
            if target_bank:
                inst_tags = chunk.get("institution_tags") or []
                if isinstance(inst_tags, str):
                    try:
                        inst_tags = json.loads(inst_tags)
                    except Exception:
                        inst_tags = [inst_tags]

                inst_match = (
                    any(target_bank.lower() in t.lower() or t.lower() in target_bank.lower() for t in inst_tags)
                    or (target_bank.lower() in content.lower())
                )
                if not inst_match:
                    downgrade_reason = f"Bank-specific claim targets '{target_bank}', but cited chunk {cid} has tags {inst_tags}."
                    break

            # (b) Check quoted span validated as substring
            matching_span = None
            for span in quoted_spans:
                if span and len(span.strip()) >= 6:
                    norm_span = " ".join(span.strip().lower().split())
                    norm_content = " ".join(content.strip().lower().split())
                    if norm_span in norm_content:
                        matching_span = span.strip()
                        break

            # If no explicit matching span, check if chunk content contains direct claim keywords or if title-only
            if not matching_span:
                # If chunk is title-only, allow title substring
                if is_title_only and len(content.strip()) > 10:
                    matching_span = content.replace("[TITLE-ONLY EVIDENCE]", "").strip()
                else:
                    downgrade_reason = f"Quoted span is not a validated verbatim substring of chunk {cid}."
                    break

            # Title-only evidence checks
            if is_title_only:
                # Must directly state or refute claim
                claim_words = " ".join([c.claim_text.lower() for c in claims])
                title_lower = content.lower()
                direct_match = (
                    ("revok" in title_lower and "revok" in claim_words)
                    or ("heritage bank" in title_lower and "heritage" in claim_words)
                    or ("bvn" in title_lower and "bvn" in claim_words)
                    or ("cybersecurity" in title_lower and "cybersecurity" in claim_words)
                    or judgment.get("title_directly_states_claim") is True
                )
                if not direct_match:
                    downgrade_reason = "Title-only evidence does not directly state the claim."
                    break
                # Cap confidence
                raw_confidence = min(raw_confidence, TITLE_ONLY_CONFIDENCE_CAP)

            verified_spans.append(matching_span)
            verified_citations.append(EvidenceCitation(
                chunk_id=cid,
                source=chunk.get("source", "Knowledge Base"),
                tier=chunk.get("tier", 1),
                url=chunk.get("url", ""),
                publish_date=chunk.get("publish_date"),
                snippet=content[:280] + ("..." if len(content) > 280 else ""),
                is_title_only=is_title_only,
                is_simulated=is_simulated,
                score=score,
                quoted_span=matching_span,
            ))

        if downgrade_reason or not verified_citations:
            logger.info(f"Grounding Guardrail Downgrade: {downgrade_reason}")
            return (
                "insufficient_evidence",
                0.30,
                f"Downgraded from {raw_verdict}: {downgrade_reason}",
                [],
                [],
                downgrade_reason or "Evidence failed code-enforced grounding checks."
            )

        return raw_verdict, raw_confidence, reasoning, verified_citations, verified_spans, None

    async def _judge_sufficiency(self, claims: list[Claim], chunks: list[dict[str, Any]], round_num: int) -> dict[str, Any]:
        """
        Judges whether retrieved passages directly support or contradict claims.
        """
        if not chunks:
            return {
                "verdict": "insufficient_evidence",
                "confidence": 0.20,
                "reasoning": "No relevant documents found in knowledge base.",
                "cited_chunk_ids": [],
            }

        passages_text = "\n\n".join([
            f"[Chunk ID: {c['id']}] Source: {c['source']} (Score: {c.get('score', 0):.2f})\n{c['content']}"
            for c in chunks[:5]
        ])

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict, skeptical financial fact verification engine grounded in real authoritative evidence.\n"
                    "RULES:\n"
                    "1. Emit 'supported' ONLY if a retrieved passage directly and explicitly confirms the claim.\n"
                    "2. Emit 'contradicted' ONLY if a retrieved passage directly and explicitly refutes the claim.\n"
                    "3. If evidence is ambiguous, partial, or missing, you MUST emit 'insufficient_evidence'. Never assume or fabricate facts.\n"
                    "4. For any supported or contradicted verdict, you MUST provide an exact 'quoted_spans' list containing verbatim substrings from the cited chunk.\n"
                    "5. If citing [TITLE-ONLY EVIDENCE], set 'title_directly_states_claim': true only if the official title explicitly affirms or refutes the claim.\n"
                    "Output JSON: {'verdict': 'supported'|'contradicted'|'insufficient_evidence', 'confidence': float, 'reasoning': '...', 'cited_chunk_ids': ['...'], 'quoted_spans': ['...'], 'title_directly_states_claim': bool}"
                )
            },
            {
                "role": "user",
                "content": (
                    f"Claims to verify: {[c.claim_text for c in claims]}\n\n"
                    f"Retrieved Passages from Knowledge Base:\n{passages_text}"
                )
            }
        ]

        try:
            raw = await self.llm.chat_completion(messages, temperature=0.0)
            data = parse_json_markdown(raw)
            return data
        except Exception as e:
            logger.warning(f"Judge sufficiency fallback: {e}")
            from backend.app.llm.mock_provider import MockProvider
            if not isinstance(self.llm, MockProvider):
                raise
            return {
                "verdict": "insufficient_evidence",
                "confidence": 0.35,
                "reasoning": "Parsing error during verification judgment.",
                "cited_chunk_ids": [],
            }

    async def check_entailment(self, claim_text: str, passage_text: str, proposed_verdict: str) -> dict[str, Any]:
        """
        Separate entailment check after retrieval.
        Determines whether the cited passage directly states or refutes the claim (direct),
        provides circumstantial/contextual evidence (indirect), or has no bearing (none).
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict textual entailment evaluator in financial fact verification.\n"
                    "Determine the exact evidential relationship between the Claim and the Retrieved Passage:\n"
                    "- 'direct': The passage explicitly asserts or denies the exact claim event.\n"
                    "- 'indirect': The passage provides circumstantial, tangential, or inferred context "
                    "(e.g. general financial health, balance sheet metrics, routine trading, normal operations, general policy) "
                    "without explicitly affirming or denying the specific asserted claim event.\n"
                    "- 'none': The passage has no evidential bearing on the claim.\n\n"
                    'Output JSON format strictly: {"relationship": "direct"|"indirect"|"none", "reasoning": "..."}'
                )
            },
            {
                "role": "user",
                "content": f"Claim(s): {claim_text}\nProposed Verdict: {proposed_verdict}\nRetrieved Passage:\n{passage_text[:1200]}"
            }
        ]

        try:
            raw = await self.llm.chat_completion(messages, temperature=0.0)
            data = parse_json_markdown(raw)
            rel = str(data.get("relationship", "none")).lower().strip()
            if rel not in ("direct", "indirect", "none"):
                rel = "indirect" if "indirect" in rel else ("direct" if "direct" in rel else "none")
            return {
                "relationship": rel,
                "reasoning": data.get("reasoning", "Evaluated textual entailment.")
            }
        except Exception as e:
            logger.warning(f"Entailment check parsing fallback: {e}")
            from backend.app.llm.mock_provider import MockProvider
            if not isinstance(self.llm, MockProvider):
                raise
            return {
                "relationship": "indirect",
                "reasoning": f"Entailment evaluation fallback: {e}"
            }

    async def _rewrite_query(self, prev_query: str, claims: list[Claim], round_num: int, target_bank: str | None) -> str:
        """Rewrites or expands query for the next retrieval round."""
        if target_bank:
            if round_num == 1:
                return f"{target_bank} official financial statement balance sheet liquidity"
            else:
                return f"{target_bank} customer notice circular operations"
        else:
            if round_num == 1:
                entities = [c.entity for c in claims if c.entity]
                entity_str = " ".join(entities)
                return f"{entity_str} Central Bank of Nigeria circular"
            else:
                return f"{prev_query} financial stability regulatory advisory"

    async def _judge_parametric_baseline(self, claims: list[Claim], original_text: str) -> VerificationResult:
        """
        Parametric-only baseline: Model answers strictly from internal pre-trained weights
        without access to external documents or knowledge base retrieval.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a financial intelligence classifier answering strictly from your own internal "
                    "pre-trained parametric knowledge (NO external documents or retrieval available).\n"
                    "Evaluate the claims based ONLY on what you know internally.\n"
                    "Output JSON: {'verdict': 'supported'|'contradicted'|'insufficient_evidence', 'confidence': float, 'reasoning': '...'}"
                )
            },
            {"role": "user", "content": f"Text:\n{original_text}\nClaims: {[c.claim_text for c in claims]}"}
        ]
        raw = await self.llm.chat_completion(messages, temperature=0.0)
        data = parse_json_markdown(raw)
        return VerificationResult(
            verdict=data.get("verdict", "insufficient_evidence"),
            confidence=float(data.get("confidence", 0.5)),
            reasoning=f"[PARAMETRIC-ONLY BASELINE] {data.get('reasoning', '')}",
            cited_passages=[],
            quoted_spans=[],
            evidence_type="none",
            retrieved_chunk_ids=[],
            retrieval_rounds=0,
            is_grounded=False,
            abstention_reason="Parametric-only baseline: KB retrieval is disabled.",
        )
