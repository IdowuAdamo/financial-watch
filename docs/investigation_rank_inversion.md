# Rank-Inversion & Benchmark v2 Deep-Dive Investigation

**Document Status**: COMPLETED  
**Date**: October 14, 2026  
**Artifact**: `docs/investigation_rank_inversion.md`  
**Reference Benchmark**: Benchmark v2 Harness (`evals/run_benchmark.py`, `evals/benchmark_results.json`)

---

## 1. Executive Summary: The "Rank Inversion" Paradox Explained

In the initial evaluation of Benchmark v2, an apparent paradox was observed:
1. **All 6 items with the gold document at Rank #1 (`seed_01`, `seed_02`, `seed_07`, `seed_08`, `seed_18`, `seed_24`) were false abstentions (`insufficient_evidence`).**
2. **All 9 correctly answered items (`seed_04`, `seed_05`, `seed_06`, `seed_09`, `seed_10`, `seed_11`, `seed_20`, `seed_21`, `seed_25`) had the gold document recorded as "outside the top 20".**

### The Core Architectural Cause
- **Why the 9 Correct Items had Gold "Outside Top 20"**:
  Every one of these 9 items was classified during Stage 3 by the deterministic `TriageGateAgent` as `scam_phishing` or `factcheck_report`. By design, to protect users from high-velocity fraud and avoid unnecessary RAG latency, scam posts bypass the iterative knowledge base retrieval loop entirely and route directly to the in-memory `ScamTypologyEngine`. Because no database retrieval was executed, `retrieved_chunk_ids` contained 0 items. The benchmark harness correctly noted that the gold regulatory circular in PostgreSQL was "not in top 20". These items succeeded via **deterministic triage routing**, not document search.
- **Why the 6 Rank #1 Items were False Abstentions**:
  All 6 items target simulated banks (*Apex Horizon Example Bank* and *Meridian Mock Bank*). Alias resolution recognized the institution, applying the `+0.25` institution boost and placing the bank's Q3 disclosure at **Rank #1**. However, under strict code-enforced grounding and secondary textual entailment checks, the general financial statement disclosures did not contain verbatim refutation of specific rumor claims (e.g., alleged revocation directives or specific hacking incidents). The entailment check returned `indirect` or `none`, capping confidence and strictly forcing a safe abstention (`insufficient_evidence`).

---

## 2. Per-Item Evidence Audit: The 15 Target Items

### Group A: The 6 Items with Gold Chunk at Rank #1 (False Abstentions)

| Seed ID | Post Text & Query Formulation | Retrieved Chunk & Score | Entailment Output | Gate That Downgraded & Evidence Tag |
| :--- | :--- | :--- | :---: | :--- |
| **`seed_01`** | **Raw**: *"Apex Horizon Example Bank don collapse completely! CBN don revoke their license yesterday night..."*<br>**Normalized**: *"Apex Horizon Example Bank has failed completely! Central Bank of Nigeria has revoked their license yesterday night..."* | `chunk_sim_apex_horizon_q3_financial_statement_md_0`<br>Score: **0.8500** (Rank 1 via bank boost) | **`indirect`**<br>(Solvency metrics do not directly affirm or refute alleged CBN revocation directive) | **Entailment Gate**: Indirect evidence capped confidence at 0.50 and forced `insufficient_evidence`.<br>Tag: `abstention_type="evidence"` |
| **`seed_02`** | **Raw**: *"Breaking news: CBN has instructed all commercial banks to stop electronic transfers to Apex Horizon Example Bank..."*<br>**Normalized**: *"Breaking news: Central Bank of Nigeria has instructed all commercial banks to stop electronic transfers to Apex Horizon Example Bank..."* | `chunk_sim_apex_horizon_q3_financial_statement_md_0`<br>Score: **0.8250** (Rank 1 via bank boost) | **`indirect`**<br>(Balance sheet discloses operations but no direct statement on electronic clearing restrictions) | **Entailment Gate**: Indirect evidence capped confidence at 0.50 and forced `insufficient_evidence`.<br>Tag: `abstention_type="evidence"` |
| **`seed_07`** | **Raw**: *"Meridian Mock Bank app has been completely down for 4 days straight. Insiders say their core database was hacked..."*<br>**Normalized**: *"Meridian Mock Bank app has been completely down for 4 days straight. Insiders say their core database was hacked..."* | `chunk_sim_meridian_mock_q3_financial_statement_md_0`<br>Score: **0.7950** (Rank 1 via bank boost) | **`none`**<br>(Q3 balance sheet disclosures do not address IT service uptime or database security breaches) | **Entailment Gate**: No evidential entailment forced downgrade to `insufficient_evidence`.<br>Tag: `abstention_type="evidence"` |
| **`seed_08`** | **Raw**: *"Customer service at Meridian Mock Bank told my colleague that their automated clearing service is frozen..."*<br>**Normalized**: *"Customer service at Meridian Mock Bank told my colleague that their automated clearing service is frozen..."* | `chunk_sim_meridian_mock_q3_financial_statement_md_0`<br>Score: **0.8120** (Rank 1 via bank boost) | **`indirect`**<br>(No explicit mention of automated clearing status in financial summary) | **Entailment Gate**: Indirect evidence forced downgrade to `insufficient_evidence`.<br>Tag: `abstention_type="evidence"` |
| **`seed_18`** | **Raw**: *"Apex Horizon Example Bank customer deposits are no longer safe. The bank has lost over 60% of liquid assets..."*<br>**Normalized**: *"Apex Horizon Example Bank customer deposits are no longer safe. The bank has lost over 60% of liquid assets..."* | `chunk_sim_apex_horizon_q3_financial_statement_md_0`<br>Score: **0.8400** (Rank 1 via bank boost) | **`indirect`**<br>(Discloses capital adequacy ratio of 18.5%, but does not explicitly refute "60% loss" phrasing) | **Entailment Gate**: Indirect evidence forced downgrade to `insufficient_evidence`.<br>Tag: `abstention_type="evidence"` |
| **`seed_24`** | **Raw**: *"Meridian Mock Bank is refusing over-the-counter cash withdrawals exceeding 20,000 Naira nationwide..."*<br>**Normalized**: *"Meridian Mock Bank is refusing over-the-counter cash withdrawals exceeding 20,000 Naira nationwide..."* | `chunk_sim_meridian_mock_q3_financial_statement_md_0`<br>Score: **0.7850** (Rank 1 via bank boost) | **`none`**<br>(Financial statements do not specify branch over-the-counter cash limits) | **Entailment Gate**: No evidential entailment forced downgrade to `insufficient_evidence`.<br>Tag: `abstention_type="evidence"` |

---

### Group B: The 9 Correctly Answered Items (Gold Outside Top 20 via Triage Bypass)

| Seed ID | Post Text & Threat Category | Triage Routing Decision | Retrieval Loop Status | Outcome & Explanation |
| :--- | :--- | :--- | :---: | :--- |
| **`seed_04`** | *"Urgent alert: CBN has approved N50,000 relief funds for all BVN holders. Click bit.ly/cbn-relief..."* | `scam_phishing` | **Bypassed (0 retrieved)** | Correctly answered `contradicted` via `ScamTypologyEngine` (fake relief grant typology). |
| **`seed_05`** | *"Congratulations! Your account has won N250,000 in the Central Bank of Nigeria National Empowerment Grant..."* | `scam_phishing` | **Bypassed (0 retrieved)** | Correctly answered `contradicted` via `ScamTypologyEngine` (empowerment grant scam). |
| **`seed_06`** | *"Security Notice: CBN is asking all bank customers to send their ATM card details and BVN to verify..."* | `scam_phishing` | **Bypassed (0 retrieved)** | Correctly answered `contradicted` via `ScamTypologyEngine` (credential harvesting). |
| **`seed_09`** | *"Apex Horizon Bank promo! Deposit N10,000 and get N50,000 in 2 hours. Approved by CBN..."* | `scam_phishing` | **Bypassed (0 retrieved)** | Correctly answered `contradicted` via `ScamTypologyEngine` (Ponzi / doubling scheme). |
| **`seed_10`** | *"Dubawa fact check alert: Beware of WhatsApp messages claiming CBN is sharing cash..."* | `factcheck_report` | **Bypassed (0 retrieved)** | Correctly answered `supported` via `ScamTypologyEngine` advisory matching. |
| **`seed_11`** | *"Urgent KYC update: Your Zenith Bank account will be blocked today unless you click here..."* | `scam_phishing` | **Bypassed (0 retrieved)** | Correctly answered `contradicted` via `ScamTypologyEngine` (KYC deactivation lure). |
| **`seed_20`** | *"Special CBN intervention: Access Bank customers can apply for N100,000 instant grant..."* | `scam_phishing` | **Bypassed (0 retrieved)** | Correctly answered `contradicted` via `ScamTypologyEngine` (fake grant typology). |
| **`seed_21`** | *"First Bank customer service WhatsApp: Send your OTP to 08039999999 to resolve reversal..."* | `scam_phishing` | **Bypassed (0 retrieved)** | Correctly answered `contradicted` via `ScamTypologyEngine` (OTP harvesting). |
| **`seed_25`** | *"FactCheckHub report: The trending link claiming CBN is giving out 2026 presidential election grants is fake..."* | `factcheck_report` | **Bypassed (0 retrieved)** | Correctly answered `supported` via `ScamTypologyEngine` advisory matching. |

---

## 3. Query Formulation & Retrieval Recall Analysis

Recall was systematically evaluated across three query formulations on all 23 verifiable benchmark items:

| Query Formulation Level | Recall@1 | In Top 5 | In Top 20 | Analysis & Bottleneck |
| :--- | :---: | :---: | :---: | :--- |
| **1. Raw Post Text** | 5 / 23 (21.7%) | 6 / 23 (26.1%) | 7 / 23 (30.4%) | Colloquial Pidgin markers (*"don comot"*, *"scatter"*) degrade embedding similarity against formal circulars. |
| **2. Normalized Pidgin Query** | 6 / 23 (26.1%) | 8 / 23 (34.8%) | 8 / 23 (34.8%) | Normalizing slang tokens to formal banking terminology restores embedding alignment on regulatory circulars. |
| **3. Pipeline Runtime Actuals** | 6 / 23 (26.1%) | 6 / 23 (26.1%) | 6 / 23 (26.1%) | Identical to Recall@1 because the 9 scam items bypassed retrieval entirely (0 chunks), while all retrieved bank items were placed directly at Rank #1 via institution boost. |

---

## 4. Run Telemetry & Error Attribution

| Telemetry Metric | Measured Value (Benchmark v2) | Status / Notes |
| :--- | :---: | :--- |
| **Total LLM Invocations** | 21 calls | 9 scam items bypassed LLM calls via deterministic triage |
| **Network Retries** | 0 | Deterministic local snapshot evaluation |
| **Request Timeouts** | 0 | Zero timeouts observed |
| **Unhandled Runtime Errors** | 0 | Pipeline executed with 100% completion rate |
| **Abstentions Tagged `evidence`** | **21 / 21 (100%)** | All abstentions were driven by rigorous grounding rules |
| **Abstentions Tagged `error/fallback`** | **0 / 21 (0%)** | Zero abstentions caused by network, parser, or LLM faults |
| **Effective False-Abstention Rate** | **34.8% (8 / 23)** | Excludes error-driven faults (unchanged because errors = 0) |

---

## 5. Re-Audit of `seed_10`

- **Item Description**: *"Dubawa fact check alert: Beware of WhatsApp messages claiming CBN is sharing cash..."*
- **Triage Decision**: Matched `factcheck_report` / `scam_phishing` keywords.
- **Assigned Advisory**: Matched in-memory advisory `internal://typology/fake_cbn_relief_grant`.
- **Audit Findings**:
  - In earlier versions, this heuristic was incorrectly attributed to CBN.
  - In Benchmark v2, `seed_10` is verified strictly against `internal://typology/fake_cbn_relief_grant` and badged in the UI/API as `[INTERNAL HEURISTIC TYPOLOGY]`.
  - The Response Agent strictly enforces Rule 3: *"NEVER state that the Central Bank of Nigeria or any bank issued this typology advisory."*

---

## 6. Dataset Parameterization & Live Provider Confirmation

- **Held-Out Dataset Path**:
  - The benchmark CLI supports `--dataset <PATH>` (defaults to `data/seed_posts.json`).
  - Held-out evaluations can be executed via:
    ```bash
    python -m evals.run_benchmark --dataset data/heldout_posts.json --provider mock
    ```
  - `data/heldout_posts.json` is explicitly ignored in `.gitignore`.
- **Live Rerun Status & Provider Transparency**:
  - The current evaluation metrics in `evals/benchmark_results.json` were produced by the **deterministic mock provider (`MockProvider` / `mock-deterministic-v1`)**, not live OpenAI API execution.
  - While the live OpenAI provider (`OpenAIProvider`) is fully implemented with SHA-256 prompt caching, running live against all 30 items consumes OpenAI credits and network calls, and was kept in `evals/provenance_audit.py` and unit tests.
