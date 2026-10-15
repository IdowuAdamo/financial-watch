# System Boundaries & Limitations: FinancialWatch

FinancialWatch is a RAG-grounded verification pipeline and reputational intelligence system tailored to the Nigerian financial services sector. Designed for high-stakes operational environments, the system prioritizes auditability, determinism, and safety over conversational flexibility.

This document outlines the explicit architectural boundaries, technical constraints, and operating limitations of the system.

---

## 1. Scope & Operating Model

- **What FinancialWatch Is**:
  - An investigative decision-support tool for institutional communications, corporate communications, and compliance teams.
  - A deterministic triage, normalization, and RAG-grounded claim verification pipeline.
  - A human-in-the-loop (HITL) approval gateway generating dual-tone response drafts (Formal Corporate + Nigerian Pidgin English).
- **What FinancialWatch Is Not**:
  - **Not an Automated Social Media Bot**: FinancialWatch will never autonomously publish posts, replies, or social media statements. All response drafts must be manually approved, edited, or rejected by human operators in the Command Center queue.
  - **Not a Real-Time High-Frequency Trading Feed**: The system is designed for rumor debunking and reputational risk analysis, not financial market forecasting or automated trade execution.
  - **Not an Open Conversational LLM**: The public intake is restricted to single-post analysis capped at 2,000 characters and rate-limited to 30 requests/minute.

---

## 2. Verification Grounding & Safe Abstention

- **Evidence Requirement**:
  - The Verifier agent operates under strict deterministic guardrails. A claim can only be marked as `supported` or `contradicted` if:
    1. A cited chunk ID exists in the retrieved set.
    2. An exact, unedited verbatim quote from that chunk is validated in Python code as a direct substring.
    3. The semantic similarity passes the relevance threshold.
    4. For bank-specific claims, the cited chunk's institution tag matches the claim's alias-resolved bank.
    5. A secondary textual entailment evaluation confirms `direct` evidence (indirect evidence caps confidence at 0.50 and forces an abstention).
- **Safe Abstention Over Parametric Guessing**:
  - If no primary circular or official disclosure directly addresses the claim, the system conservatively returns `insufficient_evidence` (confidence capped at 0.00–0.50).
  - The system will **never** guess, extrapolate, or hallucinate facts based on internal LLM parametric memory. An abstention indicates that the indexed knowledge base does not contain direct corroboration or refutation, not necessarily that the rumor is true or false.

---

## 3. Knowledge Base Domain Boundaries

- **Tier 1 Regulatory Authoritative Documents**:
  - Contains real regulatory documents directly fetched from official government repositories: Central Bank of Nigeria (CBN), Nigeria Deposit Insurance Corporation (NDIC), Securities and Exchange Commission (SEC), and verified fact-checking desks (Dubawa, FactCheckHub).
  - Each document records exact retrieval date, source URL, and full SHA-256 content checksum.
  - **Reviewed Document Exclusions:**
    - `2023-preliminaries-0df1a38b-903c-4e0f-a821-4cbabd634fc6.pdf`: reviewed, excluded: scanned/no text layer
    - `2024-Annual Report.pdf`: reviewed, excluded: unusable font encoding

- **Tier 2 Simulated Client Disclosures**:
  - To respect institutional privacy and ethical AI standards, all rumors alleging institutional collapse, fraud, or outage target strictly **fictional banks**:
    - *Apex Horizon Example Bank*
    - *Meridian Mock Bank*
    - *Northbridge Example Bank*
    - *Kreston Test Bank*
  - Corresponding Tier 2 disclosures are simulated general press statements, clearly marked with `[SIMULATED CLIENT DOCUMENT]`.
  - Real bank names appear exclusively in Tier 1 authoritative regulatory circulars (e.g., CBN published lists of licensed deposit money banks).
- **Internal Heuristic Typologies**:
  - Pre-screened scam and phishing patterns (e.g., fake CBN grant relief schemes, lottery scams) match internal heuristic rules.
  - Response drafts cite internal advisories with `internal://typology/...` identifiers and explicitly state that the advice is based on standard banking security heuristics, never attributing internal typology phrasing to CBN.

---

## 4. Linguistic & Vernacular Boundaries (Nigerian Pidgin)

- **Lexicon-Based Token Normalization**:
  - The Pidgin Normalizer employs a curated lexicon mapping colloquial Nigerian Pidgin terms and phonetic variants (e.g., *comot*, *scatter*, *chop*, *kpai*, *wahala*, *magun*, *run down*) into standardized English banking queries.
- **Language Coverage Limits**:
  - FinancialWatch does not currently support indigenous Nigerian regional languages (Yoruba, Hausa, Igbo) without pre-translation into English or Nigerian Pidgin.
  - Highly idiomatic, rapidly evolving youth slang or dialectical micro-variations not present in the normalization dictionary will bypass Pidgin rewrites and be retrieved as raw post tokens.

---

## 5. Web Ingestion & Ethical Crawling Constraints

- **Compliance Gate Pre-Requisites**:
  - All automated HTTP requests are strictly routed through the Compliance Gate.
  - The crawler identifies itself via RFC 9309 headers: `User-Agent: FinancialWatchBot/1.0 (+https://github.com/IdowuAdamo/financial-watch)`.
- **Mandatory 5-Second Crawl-Delay Floor**:
  - Crawl intervals are strictly bounded by `max(5.0, crawl_delay)`. The crawler will never hit any external regulatory or news domain faster than once every 5 seconds.
- **401/403/429 Non-Bypass**:
  - When a target website responds with HTTP 401, 403, or 429 (or exhibits Cloudflare / CAPTCHA bot challenges), the crawler immediately logs the refusal and marks the source as `manual_curation_only`.
  - The system will **never** attempt header spoofing, IP rotation, proxy rotation, or bot bypass techniques.

---

## 6. Runtime & State Persistence Constraints

- **HITL Queue Persistence Architecture**:
  - The Command Center Human-in-the-Loop (HITL) Queue is backed by a persistent PostgreSQL 16 table (`approval_queue`), with automatic schema initialization and JSONB payload storage.
  - In production and containerized environments connected to PostgreSQL / RDS, review states (`pending`, `approved`, `rejected`, `edited`), rejection audit reasons, and manual counter-narrative edits survive container restarts, ECS redeployments, and host restarts.
  - In standalone developer or offline testing environments operating without an active database connection, the API gracefully falls back to an in-memory session cache (`_ANALYZED_POSTS`). In this fallback mode, restarting the local Python process resets the queue state. The Command Center UI displays an active storage status indicator to make this explicit to operators.
- **Concurrency & Rate Limiting**:
  - Intake requests are capped at 30 requests/minute per client identifier.
  - Input post length is strictly capped at 2,000 characters.
  - LLM completion requests are cached by SHA-256 hash of `{provider, model, prompt_version, temperature, messages}` to prevent redundant compute expenditure.

---

## 7. Future Work: Web Evidence Lane Design Summary

In the current release, dynamic live-web search is intentionally omitted to preserve strict provenance determinism and protect against prompt injection or web-scraping hallucinations. The architectural design for future web evidence retrieval is structured as follows:

- **Feature Gating**:
  - Controlled by an explicit runtime environment flag: `WEB_EVIDENCE_ENABLED=false` (default off).
- **Isolated Storage Schema (`web_candidates`)**:
  - Any passages retrieved dynamically from external search APIs or secondary web lanes are quarantined into a distinct `web_candidates` table. They are **never** mixed into the core authoritative regulatory tables (`documents`, `document_chunks`).
- **Strict Tier 3 Authority Classification**:
  - All web-retrieved candidate passages are labeled as Tier 3 evidence with an automatic confidence penalty (capped at 0.60 maximum confidence score).
- **Allowlisted Search Desks**:
  - Search queries are restricted to allowlisted investigative domains (e.g., official press releases, accredited fact-checking desks like Dubawa and FactCheckHub).
- **Anti-Poisoning & Sanitization Pipeline**:
  - Dynamic web text must undergo `DocumentChunker.sanitize_untrusted_content()` to strip instruction overrides, markdown injection, and zero-width control characters.
- **Mandatory Human Approval Gate**:
  - No claim can be marked `supported` or `contradicted` exclusively based on Tier 3 web evidence without explicit Human-in-the-Loop review and confirmation in the Command Center queue.

