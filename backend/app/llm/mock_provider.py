"""
Deterministic Mock LLM Provider for automated tests, CI, and offline demos.
Provides reproducible structured agent responses without requiring external API keys.
"""
import hashlib
import json
import logging

import numpy as np

from backend.app.llm.base import LLMProvider

logger = logging.getLogger("financial_watch.llm.mock")

class MockProvider(LLMProvider):
    """
    Deterministic provider providing rule-based, reproducible agent responses.
    """
    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1000,
        response_format: dict[str, str] | None = None,
    ) -> str:
        prompt_content = "\n".join([m.get("content", "") for m in messages])
        prompt_lower = prompt_content.lower()

        # 0. PARAMETRIC-ONLY BASELINE (Ablation: model answers strictly from internal pre-trained weights)
        if "parametric-only baseline" in prompt_lower or "internal parametric knowledge" in prompt_lower:
            # Ungrounded model lacks external KB and guesses on several rumors
            if "heritage bank" in prompt_lower and ("revok" in prompt_lower or "licence" in prompt_lower):
                return json.dumps({
                    "verdict": "contradicted",
                    "confidence": 0.70,
                    "reasoning": "Model internal memory recalls rumors of bank distress as unconfirmed."
                })
            elif "kreston" in prompt_lower:
                return json.dumps({
                    "verdict": "supported" if "raid" in prompt_lower or "collapse" in prompt_lower else "contradicted",
                    "confidence": 0.65,
                    "reasoning": "Parametric hallucination: Model evaluates fictional entity without checking registry."
                })
            elif "windfall tax" in prompt_lower or "branch" in prompt_lower:
                return json.dumps({
                    "verdict": "contradicted",
                    "confidence": 0.60,
                    "reasoning": "Parametric baseline assumes regulatory denial without citing gazettes."
                })
            elif "bvn" in prompt_lower and "expir" in prompt_lower:
                return json.dumps({
                    "verdict": "contradicted",
                    "confidence": 0.80,
                    "reasoning": "Model recalls general BVN stability."
                })
            elif "maintenance" in prompt_lower or "app down" in prompt_lower:
                return json.dumps({
                    "verdict": "supported",
                    "confidence": 0.75,
                    "reasoning": "Model assumes IT upgrade claims are plausible."
                })
            else:
                return json.dumps({
                    "verdict": "insufficient_evidence",
                    "confidence": 0.40,
                    "reasoning": "Parametric baseline cannot locate specific circular in internal memory."
                })

        # 0.1 TEXTUAL ENTAILMENT EVALUATOR GATE
        if "textual entailment evaluator" in prompt_lower or "exact evidential relationship" in prompt_lower:
            # Re-check seed_01 rule: Apex Horizon financial statement is indirect evidence of license revocation
            if "apex horizon" in prompt_lower and ("revok" in prompt_lower or "licence" in prompt_lower or "license" in prompt_lower):
                return json.dumps({
                    "relationship": "indirect",
                    "reasoning": "Passage confirms ongoing clearing operations and balance sheet liquidity; this is indirect circumstantial context, not a direct statement affirming or denying license revocation."
                })
            elif "heritage bank" in prompt_lower:
                return json.dumps({
                    "relationship": "direct",
                    "reasoning": "Official CBN circular title directly states the revocation of Heritage Bank Plc license."
                })
            elif "bvn" in prompt_lower and "expir" in prompt_lower:
                return json.dumps({
                    "relationship": "direct",
                    "reasoning": "Official circular directly states that BVN has no expiration date."
                })
            elif "meridian mock" in prompt_lower:
                return json.dumps({
                    "relationship": "direct",
                    "reasoning": "Client advisory directly states planned mobile application connectivity latency during upgrade."
                })
            elif "northbridge" in prompt_lower and ("fee" in prompt_lower or "recruitment" in prompt_lower or "interview" in prompt_lower):
                return json.dumps({
                    "relationship": "direct",
                    "reasoning": "Client security advisory explicitly states the bank does not request application processing fees."
                })
            elif "northbridge" in prompt_lower and "800-example" in prompt_lower:
                return json.dumps({
                    "relationship": "direct",
                    "reasoning": "Client advisory directly lists the official corporate helpline."
                })
            elif "cybersecurity levy" in prompt_lower:
                return json.dumps({
                    "relationship": "direct",
                    "reasoning": "Official circular directly provides guidance on cybersecurity levy withdrawal."
                })
            elif "recapitalization" in prompt_lower or "minimum capital" in prompt_lower:
                return json.dumps({
                    "relationship": "direct",
                    "reasoning": "Official circular directly documents minimum capital requirements."
                })
            elif "cardoso" in prompt_lower or "grant" in prompt_lower or "investment" in prompt_lower:
                return json.dumps({
                    "relationship": "direct",
                    "reasoning": "Official public alert directly warns against fraudulent investment and grant schemes."
                })
            elif "legal tender" in prompt_lower or "old naira" in prompt_lower:
                return json.dumps({
                    "relationship": "direct",
                    "reasoning": "Official circular directly confirms legal tender status of banknotes."
                })
            else:
                return json.dumps({
                    "relationship": "none",
                    "reasoning": "Passage does not bear direct evidential entailment to the asserted claim."
                })

        # 1. TRIAGE GATE
        if "triage" in prompt_lower or "classify the primary nature of this post" in prompt_lower:
            if any(k in prompt_lower for k in ["bvn", "pin", "otp", "whatsapp", "telegram", "urgent", "freeze", "free grant", "bonus", "winner", "reward", "recruitment", "relieflink", "http"]):
                return json.dumps({
                    "post_type": "scam_phishing",
                    "requires_deep_verification": False,
                    "urgency_level": "high",
                    "reasoning": "Post exhibits classic scam/phishing indicators (credential request, fee for job, or urgent unsolicited reward)."
                })
            else:
                return json.dumps({
                    "post_type": "reputational_rumour",
                    "requires_deep_verification": True,
                    "urgency_level": "medium",
                    "reasoning": "Post targets banking solvency, regulatory licensing, or customer operations requiring factual knowledge base verification."
                })

        # 2. CLAIM EXTRACTION
        if "claim extraction" in prompt_lower or "extract discrete" in prompt_lower:
            entity = "Banking Institution"
            if "apex horizon" in prompt_lower:
                entity = "Apex Horizon Example Bank"
            elif "meridian" in prompt_lower:
                entity = "Meridian Mock Bank"
            elif "northbridge" in prompt_lower:
                entity = "Northbridge Example Bank"
            elif "kreston" in prompt_lower:
                entity = "Kreston Test Bank"
            elif "heritage" in prompt_lower:
                entity = "Heritage Bank Plc"
            elif "cbn" in prompt_lower or "central bank" in prompt_lower:
                entity = "Central Bank of Nigeria"

            claims = []
            if "revoke" in prompt_lower or "licence" in prompt_lower or "license" in prompt_lower:
                claims.append({
                    "claim_id": "c1",
                    "claim_text": f"The operating banking licence of {entity} has been revoked by the regulatory authority.",
                    "entity": entity,
                    "topic": "license_revocation"
                })
            elif "distress" in prompt_lower or "bank run" in prompt_lower or "withdraw" in prompt_lower or "insolvent" in prompt_lower or "collapse" in prompt_lower:
                claims.append({
                    "claim_id": "c2",
                    "claim_text": f"{entity} is insolvent and depositors are urged to withdraw funds immediately.",
                    "entity": entity,
                    "topic": "bank_distress"
                })
            elif "upgrade" in prompt_lower or "maintenance" in prompt_lower or "app" in prompt_lower or "down" in prompt_lower:
                claims.append({
                    "claim_id": "c3",
                    "claim_text": f"{entity} mobile banking channels are down due to planned IT maintenance.",
                    "entity": entity,
                    "topic": "systems_outage"
                })
            elif "recruiting" in prompt_lower or "graduate trainee" in prompt_lower or "fee" in prompt_lower:
                claims.append({
                    "claim_id": "c4",
                    "claim_text": f"{entity} requires applicants to pay fees for recruitment aptitude testing.",
                    "entity": entity,
                    "topic": "recruitment_fraud"
                })
            elif "hotline" in prompt_lower or "customer service" in prompt_lower:
                claims.append({
                    "claim_id": "c5",
                    "claim_text": f"{entity} official customer service hotline is +234 1 800-EXAMPLE.",
                    "entity": entity,
                    "topic": "customer_support"
                })
            elif "recapitalization" in prompt_lower or "capital" in prompt_lower:
                claims.append({
                    "claim_id": "c6",
                    "claim_text": "CBN requires commercial banks with international authorization to increase capital to N500 Billion.",
                    "entity": "Central Bank of Nigeria",
                    "topic": "recapitalization"
                })
            elif "cybersecurity levy" in prompt_lower:
                claims.append({
                    "claim_id": "c7",
                    "claim_text": "CBN has officially withdrawn circular on the 0.5% cybersecurity levy.",
                    "entity": "Central Bank of Nigeria",
                    "topic": "cybersecurity_levy"
                })
            elif "naira" in prompt_lower or "legal tender" in prompt_lower:
                claims.append({
                    "claim_id": "c8",
                    "claim_text": "Older banknotes have ceased to be legal tender in Nigeria.",
                    "entity": "Central Bank of Nigeria",
                    "topic": "currency_demonetization"
                })
            else:
                claims.append({
                    "claim_id": "c1",
                    "claim_text": prompt_content[:120].strip(),
                    "entity": entity,
                    "topic": "general_claim"
                })
            return json.dumps({"claims": claims})

        # 3. VERIFICATION AGENT (Bounded Retrieval Judge)
        if "verification agent" in prompt_lower or "judge sufficiency" in prompt_lower or "verdict" in prompt_lower:
            # 3.1 Kreston Test Bank: Unverified Control - MUST ABSTAIN
            if "kreston" in prompt_lower:
                return json.dumps({
                    "verdict": "insufficient_evidence",
                    "confidence": 0.25,
                    "reasoning": "Kreston Test Bank is an unverified entity with no records in knowledge base.",
                    "cited_chunk_ids": [],
                    "quoted_spans": [],
                    "title_directly_states_claim": False,
                    "abstention_reason": "No corporate disclosures or regulatory circulars exist for Kreston Test Bank."
                })

            # 3.2 Unverified Policy Rumors (Windfall tax, village branch closure, N500 maintenance)
            if any(k in prompt_lower for k in ["windfall tax", "secret memo", "small town", "village", "daily maintenance charge"]):
                return json.dumps({
                    "verdict": "insufficient_evidence",
                    "confidence": 0.25,
                    "reasoning": "No authoritative regulatory circular confirms or denies this policy rumor.",
                    "cited_chunk_ids": [],
                    "quoted_spans": [],
                    "title_directly_states_claim": False,
                    "abstention_reason": "No official CBN directive found in Tier 1 publications."
                })

            # 3.3 Heritage Bank Revocation (June 3, 2024)
            if "heritage bank" in prompt_lower:
                return json.dumps({
                    "verdict": "supported",
                    "confidence": 0.95,
                    "reasoning": "Official CBN circular explicitly confirms revocation of Heritage Bank Plc licence on June 3, 2024.",
                    "cited_chunk_ids": ["chunk_cbn_title_7472"],
                    "quoted_spans": ["CBN Revokes the Banking Licence of Heritage Bank Plc"],
                    "title_directly_states_claim": True,
                })

            # 3.4 Apex Horizon Example Bank
            if "apex horizon" in prompt_lower:
                if any(k in prompt_lower for k in ["revok", "distress", "bank run", "withdraw", "kudi"]):
                    return json.dumps({
                        "verdict": "contradicted",
                        "confidence": 0.90,
                        "reasoning": "Client Q3 financial statements contradict insolvency rumors: clearing operations remain fully operational.",
                        "cited_chunk_ids": ["sim_apex_horizon_q3_financial_statement_c000"],
                        "quoted_spans": ["electronic clearing operations, real-time gross settlement transactions, and daily interbank counterparty commitments remain fully operational"],
                        "title_directly_states_claim": False,
                    })
                else:
                    return json.dumps({
                        "verdict": "supported",
                        "confidence": 0.92,
                        "reasoning": "Client Q3 financial statement confirms customer deposits expanded by 11.2% year-to-date.",
                        "cited_chunk_ids": ["sim_apex_horizon_q3_financial_statement_c000"],
                        "quoted_spans": ["customer deposits expanded by 11.2% year-to-date"],
                        "title_directly_states_claim": False,
                    })

            # 3.5 Meridian Mock Bank (Maintenance / Outage)
            if "meridian mock" in prompt_lower:
                return json.dumps({
                    "verdict": "supported",
                    "confidence": 0.88,
                    "reasoning": "Official client IT advisory confirms scheduled routine maintenance during off-peak weekend hours.",
                    "cited_chunk_ids": ["sim_meridian_mock_it_advisory_c000"],
                    "quoted_spans": ["brief intermittent connectivity on the Meridian Mock mobile application and USSD services"],
                    "title_directly_states_claim": False,
                })

            # 3.6 Northbridge Example Bank
            if "northbridge" in prompt_lower:
                if any(k in prompt_lower for k in ["recruiting", "recruitment", "interview", "fee", "12,500", "15k"]):
                    return json.dumps({
                        "verdict": "contradicted",
                        "confidence": 0.94,
                        "reasoning": "Client security advisory explicitly states bank never charges application or aptitude test fees.",
                        "cited_chunk_ids": ["sim_northbridge_example_security_advisory_c000"],
                        "quoted_spans": ["The bank does not request application processing fees, interview scheduling charges, or background check payments"],
                        "title_directly_states_claim": False,
                    })
                elif "hotline" in prompt_lower or "800-example" in prompt_lower:
                    return json.dumps({
                        "verdict": "supported",
                        "confidence": 0.92,
                        "reasoning": "Security advisory confirms official customer service helpline +234 1 800-EXAMPLE.",
                        "cited_chunk_ids": ["sim_northbridge_example_security_advisory_c000"],
                        "quoted_spans": ["Customer Support Line: +234 1 800-EXAMPLE"],
                        "title_directly_states_claim": False,
                    })
                else:
                    return json.dumps({
                        "verdict": "contradicted",
                        "confidence": 0.95,
                        "reasoning": "Client advisory clarifies corporate security protocols.",
                        "cited_chunk_ids": ["sim_northbridge_example_security_advisory_c000"],
                        "quoted_spans": ["The bank does not request application processing fees, interview scheduling charges, or background check payments"],
                        "title_directly_states_claim": False,
                    })

            # 3.7 BVN Expiration Rumor
            if "bvn" in prompt_lower and any(k in prompt_lower for k in ["expir", "10 year", "5000", "5k"]):
                return json.dumps({
                    "verdict": "contradicted",
                    "confidence": 0.96,
                    "reasoning": "Official CBN press statement confirms BVN issued in Nigeria has no expiry date.",
                    "cited_chunk_ids": ["chunk_cbn_title_7107"],
                    "quoted_spans": ["Press Release: BVN Issued in Nigeria Has No Expiry Date - CBN"],
                    "title_directly_states_claim": True,
                })

            # 3.8 Cybersecurity Levy Withdrawal
            if "cybersecurity levy" in prompt_lower or "0.5%" in prompt_lower:
                return json.dumps({
                    "verdict": "supported",
                    "confidence": 0.90,
                    "reasoning": "Official CBN circular confirms withdrawal of implementation circular on 0.5% cybersecurity levy.",
                    "cited_chunk_ids": ["chunk_cbn_title_7463"],
                    "quoted_spans": ["Implementation Guidance on the Collection and Remittance of the National Cybersecurity Levy"],
                    "title_directly_states_claim": True,
                })

            # 3.9 Bank Recapitalization
            if "recapitalization" in prompt_lower or "minimum capital" in prompt_lower or "500 billion" in prompt_lower:
                if "tomorrow" in prompt_lower or "seized" in prompt_lower:
                    return json.dumps({
                        "verdict": "contradicted",
                        "confidence": 0.92,
                        "reasoning": "CBN recapitalization framework contradicts arbitrary seizure claims.",
                        "cited_chunk_ids": ["chunk_cbn_title_7414"],
                        "quoted_spans": ["Review of Minimum Capital Requirements for Commercial, Merchant and Non-Interest Banks in Nigeria"],
                        "title_directly_states_claim": True,
                    })
                else:
                    return json.dumps({
                        "verdict": "supported",
                        "confidence": 0.94,
                        "reasoning": "Official CBN circular confirms minimum capital requirements for commercial banks.",
                        "cited_chunk_ids": ["chunk_cbn_title_7414"],
                        "quoted_spans": ["Review of Minimum Capital Requirements for Commercial, Merchant and Non-Interest Banks in Nigeria"],
                        "title_directly_states_claim": True,
                    })

            # 3.10 Fake Grant / Cardoso Investment Fraud
            if any(k in prompt_lower for k in ["presidential grant", "relief fund", "50,000", "50k", "cardoso", "40% monthly"]):
                return json.dumps({
                    "verdict": "contradicted",
                    "confidence": 0.95,
                    "reasoning": "Official CBN public warning explicitly alerts against fraudulent relief funds and investment schemes.",
                    "cited_chunk_ids": ["chunk_cbn_title_6182"],
                    "quoted_spans": ["Beware of Fraudulent Activities"],
                    "title_directly_states_claim": True,
                })

            # 3.11 Old Banknote Demonetization
            if "old naira" in prompt_lower or "older 200" in prompt_lower or "legal tender" in prompt_lower:
                return json.dumps({
                    "verdict": "contradicted",
                    "confidence": 0.88,
                    "reasoning": "Official CBN announcements confirm all denominations of naira notes remain legal tender indefinitely.",
                    "cited_chunk_ids": ["chunk_cbn_title_229"],
                    "quoted_spans": ["Official Central Bank of Nigeria Regulatory Document"],
                    "title_directly_states_claim": True,
                })

            # Default: insufficient_evidence
            return json.dumps({
                "verdict": "insufficient_evidence",
                "confidence": 0.30,
                "reasoning": "No authoritative regulatory circular or client publication confirms or denies this assertion.",
                "cited_chunk_ids": [],
                "quoted_spans": [],
                "title_directly_states_claim": False,
                "abstention_reason": "No direct factual proof located in knowledge base."
            })

        # 4. CLASSIFICATION AGENT
        if "classification agent" in prompt_lower or "classify the post into" in prompt_lower:
            if "scam_phishing" in prompt_lower or any(k in prompt_lower for k in ["otp", "pin", "reward", "recruitment fee", "telegram", "grant"]):
                category = "scam_impersonation"
                rationale = "Post solicits sensitive credentials, payment of fees, or exploits fraudulent incentives."
            elif "contradicted" in prompt_lower:
                category = "misinformation"
                rationale = "Claim contradicts official regulatory gazettes or client disclosures."
            elif "supported" in prompt_lower:
                category = "credible"
                rationale = "Claim directly aligns with verified authoritative announcements."
            else:
                category = "unverified"
                rationale = "Evidence is insufficient to confirm or refute the claim."
            
            return json.dumps({"category": category, "rationale": rationale})

        # 5. RESPONSE AGENT
        if "response agent" in prompt_lower or "draft counter-message" in prompt_lower:
            return json.dumps({
                "formal_response": (
                    "Official Public Clarification: Claims circulating regarding banking distress or license revocation "
                    "are false and unverified. According to Central Bank of Nigeria publications, the banking system "
                    "remains fully solvent and operational. Customers are advised to rely strictly on official directives."
                ),
                "pidgin_response": (
                    "Make una no panic o! No bank license don dey revoked by CBN. All customer money dey safe "
                    "and banks dey work well. Check official circular before you believe social media rumors."
                ),
                "cited_chunk_ids": ["chunk_cbn_title_7472"],
                "citation_validation_status": "VALID",
            })

        # Default fallback
        return json.dumps({"message": "Deterministic mock completion", "input_length": len(prompt_content)})

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._deterministic_vector(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        return self._deterministic_vector(query)

    def _deterministic_vector(self, text: str) -> list[float]:
        h = hashlib.md5(text.encode("utf-8")).digest()
        seed = int.from_bytes(h[:4], "big")
        rng = np.random.RandomState(seed)
        vec = rng.randn(self.dimensions).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()
