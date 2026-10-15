# FinancialWatch: Knowledge Base Governance, Compliance & Source Provenance

## 1. Compliance Architecture & Crawler Ethics

FinancialWatch implements strict regulatory and ethical crawling protocols governed by RFC 9309. The crawling engine (`memory/compliance/gate.py`) is decoupled from ingestion parsers and strictly controls all outbound HTTP traffic.

### 1.1 Non-Negotiable Crawler Rules
1. **Identified User-Agent:** All HTTP requests transmit the explicit identifying agent:
   ```http
   User-Agent: FinancialWatchBot/1.0 (+https://github.com/client/financial-watch)
   ```
2. **Strict RFC 9309 Robots Respect:** `robots.txt` files are fetched, parsed, and cached locally for 24 hours. If a path is disallowed, the compliance gate immediately rejects the request.
3. **Crawl-Delay Enforcement:** A mandatory per-domain crawl delay (minimum 5.0 seconds for `cbn.gov.ng` and `ndic.gov.ng`) is enforced across concurrent tasks to avoid server degradation.
4. **The 403 / 401 Manual-Only Rule:** Any resource returning `HTTP 401 Unauthorized` or `HTTP 403 Forbidden` (such as Cloudflare bot protection on CBN binary PDFs) is **immediately marked as manual-only**. Under no circumstances does FinancialWatch employ header spoofing, `Referer` trickery, or rotating User-Agent workarounds.
5. **Conservative 404 Abort:** Resources returning `HTTP 404 Not Found` abort immediately without exponential retry storms.

---

## 2. Authoritative Source Registry

The source registry (`memory/registry/sources.yaml`) defines three strict trust tiers:

```
┌──────────────────────────────────────────────────────────────┐
│                    TRUST TIER HIERARCHY                      │
├──────────────────────────────────────────────────────────────┤
│ Tier 1: Authoritative Primary Regulators                     │
│         • Central Bank of Nigeria (cbn.gov.ng)               │
│         • Nigeria Deposit Insurance Corp (ndic.gov.ng)       │
│         • Securities & Exchange Commission (sec.gov.ng)      │
├──────────────────────────────────────────────────────────────┤
│ Tier 2: Certified Fact-Checking Organizations               │
│         • FactCheckHub (factcheckhub.com)                    │
│         • Dubawa Nigeria (dubawa.org)                        │
├──────────────────────────────────────────────────────────────┤
│ Tier 3: Verified Client Disclosures (Simulated)              │
│         • [SIMULATED CLIENT DOCUMENT] Official Disclosures   │
│         • Corporate statements, Q3 financial positions       │
└──────────────────────────────────────────────────────────────┘
```

### Domain Audit Findings

| Source | Domain | Robots Status | Crawler Policy | Observed Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **CBN** | `cbn.gov.ng` | Allowed (`/Documents/`, `/NewsArchive/`) | 5.0s crawl delay | HTML pages accessible; binary PDFs in `/Out/` protected by Cloudflare bot management (HTTP 403). Handled via manual download list. |
| **NDIC** | `ndic.gov.ng` | Timeout / Inactive | Backoff & Unconfirmed | Connection timeouts on direct automated crawl. Marked unconfirmed pending browser validation. |
| **SEC Nigeria** | `sec.gov.ng` | Allowed (`/rules/`, `/circulars/`) | 5.0s crawl delay | Public enforcement actions and crypto-asset advisories accessible. |
| **Dubawa** | `dubawa.org` | Timeout / Inactive | Backoff & Unconfirmed | Treated as unconfirmed; manual verification required. |
| **FactCheckHub** | `factcheckhub.com`| Inactive | Backoff & Unconfirmed | Marked unconfirmed; automated fallback to primary regulator circulars. |

---

## 3. The Central Bank of Nigeria (CBN) GetAllDocuments Endpoint

### 3.1 Endpoint Discovery & Ingestion
During sitemap exploration, an undocumented JSON endpoint was identified:
- **URL:** `https://www.cbn.gov.ng/api/GetAllDocuments`
- **Method:** `GET`
- **Audit Action:** Fetched exactly once through the compliance gate with the identifying User-Agent on 2026-10-14.
- **Raw Storage:** Archived in `memory/raw_store/cbn_get_all_documents_raw.json` (7,362 records, 1,768,092 bytes).
- **Cryptographic Provenance:** SHA-256 hash `6902172f6fab12d8a39a7388e404b89ebcbf122941db9d3da14cf2996d933ca3`.

### 3.2 Stability Warning & Governance Policy
> [!WARNING]
> **Undocumented & Unstable API Endpoint**
> The `GetAllDocuments` endpoint is an unversioned, internal backend API of the CBN website. It is subject to breaking schema modifications, rate limiting, or complete removal without notice. The FinancialWatch crawler treats this snapshot as a point-in-time index cache and does NOT poll this endpoint continually in production.

### 3.3 Title-Only Evidence Handling
The 7,362 records contain document titles, publication dates, and category classifications, but lack the full text body of the circulars. To preserve safety:
1. **Weight Penalty:** Title-only records receive a **0.65x weighting multiplier** in hybrid search re-ranking.
2. **Explicit Verification Labeling:** If the Verification Agent grounds a finding on a title-only document, the result must display the badge: `[TITLE-ONLY EVIDENCE]`.
3. **Mandatory Manual Escalation:** The response generated for title-only evidence warns the compliance officer that the underlying full text was not parsed and directs them to verify the official circular directly.

---

## 4. Manual Download Candidate Register

When Cloudflare blocks automated PDF downloads, documents are staged in `memory/manual/download_list.md` for human operator retrieval:

| Reference No. | Document Title | Publication Date | Official Source URL |
| :--- | :--- | :--- | :--- |
| `BSD/DIR/GEN/LAB/17/004` | Directory of Licensed Commercial Banks in Nigeria | 2024-03-28 | `https://www.cbn.gov.ng/Out/2024/BSD/LicensedBanksDirectoryMarch2024.pdf` |
| `CCD/PR/GEN/01/014` | Revocation of the Banking Licence of Heritage Bank Plc | 2024-06-03 | `https://www.cbn.gov.ng/Out/2024/CCD/CBN Press Release Heritage 030624.pdf` |
| `FPR/DIR/PUB/CIR/002/009` | Review of Minimum Capital Requirements for Commercial Banks | 2024-03-28 | `https://www.cbn.gov.ng/Out/2024/FPD/RecapitalisationCircular2024.pdf` |
| `CCD/PR/GEN/01/008` | Clarification on Bank Verification Number (BVN) Expiry | 2023-05-10 | `https://www.cbn.gov.ng/Out/2023/CCD/CBN Press Release BVN 100523.pdf` |
| `BPS/DIR/GEN/CIR/01/021` | Mandatory National Identification Number (NIN) Linkage | 2023-12-01 | `https://www.cbn.gov.ng/Out/2023/BPS/NIN_BVN_Linkage_Mandate.pdf` |
| `BSD/DIR/GEN/CIR/14/032` | Statement on the Safety and Soundness of the Nigerian Banking System | 2024-01-10 | `https://www.cbn.gov.ng/Out/2024/BSD/BankingSystemStabilityJan2024.pdf` |
| `BSD/DIR/GEN/CIR/12/019` | Public Advisory: Proliferation of Fraudulent Loan Apps | 2023-08-15 | `https://www.cbn.gov.ng/Out/2023/BSD/IllegalLoanAppsAdvisory.pdf` |
| `BPS/DIR/GEN/CIR/15/007` | Cybersecurity Advisory: OTP Interception and Social Engineering | 2024-04-12 | `https://www.cbn.gov.ng/Out/2024/BPS/CyberAdvisoryOTP2024.pdf` |
| `NDIC/DIS/CIR/2024/01` | Maximum Deposit Insurance Coverage Limits Review | 2024-05-02 | `https://ndic.gov.ng/circulars/DepositInsuranceCoverageIncrease2024.pdf` |
| `SEC/CMR/ADV/04/2024` | Public Notice: Unauthorized Digital Asset Trading Platforms | 2024-04-18 | `https://sec.gov.ng/advisories/UnauthorizedCryptoPlatforms2024.pdf` |
| `FCCPC/ADV/2024/02` | Joint Regulatory Task Force Notice on Digital Lending Violations | 2024-02-20 | `https://fccpc.gov.ng/notices/DigitalLendingAdvisory2024.pdf` |

---

## 5. Simulated Client Documents & Fictional Institution Safeguards

To benchmark bank-specific rumours without fabricating official statements for real operating institutions:
1. **Fictional Entity Roster:**
   - `Apex Horizon Example Bank` (Fictional commercial bank)
   - `Meridian Mock Bank` (Fictional merchant bank)
   - `Northbridge Example Bank` (Fictional regional bank)
   - `Kreston Test Bank` (Unverified control bank with NO client document, for testing system abstention)
2. **Mandatory Tagging:** Every chunk extracted from simulated client documents embeds the immutable token: `[SIMULATED CLIENT DOCUMENT]`.
3. **Plausible 2026 Disclosures:** Simulated documents reflect realistic financial metrics (e.g., 18.2% Capital Adequacy Ratio, positive liquidity coverage) dated plausibly in 2026.
4. **No Quoted Thresholds from Memory:** Regulatory criteria (e.g. minimum capital requirements) in simulated files cite only verified official circulars or generic operational statements.
