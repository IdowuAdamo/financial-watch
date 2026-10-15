# FinancialWatch: Manual Download List (Action Required)

**Status:** MANUAL DOWNLOAD REQUIRED (Bot Protection / 403 on Target Portals)  
**Last Updated:** October 15, 2026  

Due to strict server-side bot protection on official regulatory portals (Cloudflare / Incapsula / HTTP 403), these authoritative documents must be downloaded manually using a standard browser and placed into `memory/manual/`.

Each downloaded file must be accompanied by a JSON sidecar file of the exact same basename (`<filename>.json`) with provenance metadata.

---

## Sidecar JSON Template

For every downloaded file (e.g. `cbn_heritage_bank_revocation_2024.pdf`), save a matching `cbn_heritage_bank_revocation_2024.json`:

```json
{
  "source_url": "https://www.cbn.gov.ng/Out/2024/CCD/CBN Press Release Heritage 030624.pdf",
  "retrieved_on": "2026-10-15T09:00:00Z",
  "publish_date": "2024-06-03",
  "title": "CBN Revokes the Banking Licence of Heritage Bank Plc",
  "tier": 1,
  "publisher": "Central Bank of Nigeria"
}
```

---

## Documents to Download

| # | Document Title | Reference No. | Official Publication Date | Direct Official URL | Suggested Target File & Sidecar |
|---|---|---|---|---|---|
| **1** | **CBN Revokes the Banking Licence of Heritage Bank Plc** | `CCD/PR/2024/001` | 2024-06-03 | [Download URL](https://www.cbn.gov.ng/Out/2024/CCD/CBN%20Press%20Release%20Heritage%20030624.pdf) | `cbn_heritage_bank_revocation_2024.pdf`<br>`cbn_heritage_bank_revocation_2024.json` |
| **2** | **Review of Minimum Capital Requirements for Commercial, Merchant and Non-Interest Banks** | `FPR/DIR/PUB/CIR/002/009` | 2024-03-28 | [Download URL](https://www.cbn.gov.ng/Out/2024/CCD/Recapitalization_MARCH_2024.pdf) | `cbn_minimum_capital_recapitalization_2024.pdf`<br>`cbn_minimum_capital_recapitalization_2024.json` |
| **3** | **Press Release: BVN Issued in Nigeria Has No Expiry Date** | `CCD/PR/2023/005` | 2023-05-10 | [Download URL](https://www.cbn.gov.ng/Out/2023/CCD/CBN%20Press%20Release%20BVN%20100523.pdf) | `cbn_bvn_no_expiry_press_release.pdf`<br>`cbn_bvn_no_expiry_press_release.json` |
| **4** | **List of Deposit Money Banks and Financial Holding Companies Operating in Nigeria** | `FPRD/DIR/PUB/01/001` | 2024-01-01 | [Download URL](https://www.cbn.gov.ng/Out/2016/FPRD/DMBs%20Database%2027-01-2016.pdf) | `cbn_licensed_deposit_money_banks.pdf`<br>`cbn_licensed_deposit_money_banks.json` |
| **5** | **Withdrawal Circular on Collection of National Cybersecurity Levy** | `PSMD/DIR/PUB/CIR/001/048` | 2024-05-17 | [Download URL](https://www.cbn.gov.ng/Out/2024/CCD/WITHDRAWAL%20CIRCULAR%20ON%20CYBERSECURITY%20LEVY%2017052024.pdf) | `cbn_withdrawal_cybersecurity_levy_circular.pdf`<br>`cbn_withdrawal_cybersecurity_levy_circular.json` |
| **6** | **Press Release: CBN Alerts Public to Fraudulent Messages and Cyber Security Attacks** | `CCD/PR/2026/002` | 2026-03-01 | [Download URL](https://www.cbn.gov.ng/Out/2026/CCD/Press%20Release%20on%20Cyber%20Security.pdf) | `cbn_fraud_and_cybersecurity_alert_2026.pdf`<br>`cbn_fraud_and_cybersecurity_alert_2026.json` |
| **7** | **Advisory on Fraudulent Claims and Fictitious Contracts Purportedly from the CBN** | `CCD/ADV/2025/003` | 2025-05-12 | [Download URL](https://www.cbn.gov.ng/Out/2025/CCD/CBN%20Press%20Release%20120525.pdf) | `cbn_fraudulent_contract_claims_advisory.pdf`<br>`cbn_fraudulent_contract_claims_advisory.json` |
| **8** | **Public Advisory: Beware of Fraudulent Loan Offers and Investment Schemes** | `CCD/ADV/2020/001` | 2020-04-01 | [Download URL](https://www.cbn.gov.ng/Out/2020/CCD/bewareoffraud.pdf) | `cbn_fraudulent_loan_offers_advisory.pdf`<br>`cbn_fraudulent_loan_offers_advisory.json` |
| **9** | **Circular on Tier 1 Wallets & Accounts, Guidance Note & Profiling of Customers** | `PSMD/DIR/PUB/CIR/001/053` | 2023-12-01 | [Download URL](https://www.cbn.gov.ng/Out/2023/PSMD/Circular%20on%20Tier%201%20Wallets%20&%20Accounts,%20Guidance%20Note%20&%20Profiling%20of%20Customers'%20Accounts%20&%20Wallets.pdf) | `cbn_tier1_wallets_account_profiling.pdf`<br>`cbn_tier1_wallets_account_profiling.json` |
| **10** | **NDIC Press Release: Review of Maximum Deposit Insurance Coverage to N5,000,000 for DMBs** | `NDIC/PR/2024/004` | 2024-05-02 | [NDIC Press Section](https://ndic.gov.ng/news/press-releases) | `ndic_deposit_insurance_coverage_increase.html`<br>`ndic_deposit_insurance_coverage_increase.json` |
| **11** | **Africa Check: Viral Claim that CBN is Giving N50,000 Relief Funds or Grants is False** | `AC-FACT-2023-011` | 2023-11-15 | [Fact Check Article](https://africacheck.org/fact-checks/reports/no-central-bank-nigeria-not-giving-n50000-grants-phishing-link) | `africacheck_cbn_fake_grants_investigation.html`<br>`africacheck_cbn_fake_grants_investigation.json` |
| **12** | **FactCheckHub: Investigation into Fake Presidential / CBN Relief Fund Portals** | `FCH-ECON-2024-002` | 2024-02-10 | [FactCheckHub Article](https://factcheckhub.com/) | `factcheckhub_cbn_grant_debunk.html`<br>`factcheckhub_cbn_grant_debunk.json` |

---

## Ingestion Workflow

Once downloaded files and JSON sidecars are placed into `memory/manual/`, the automated manual ingestion engine will:
1. Validate presence of corresponding `.json` sidecars.
2. Compute the exact SHA-256 byte checksum of each raw document file.
3. Record `retrieved_on` separately from official `publish_date`.
4. Parse text (using `pypdf` for `.pdf` and `BeautifulSoup4` for `.html`), chunk with metadata, generate embeddings, and insert directly into PostgreSQL `documents` and `document_chunks`.
5. Re-export the compacted snapshot (`kb_snapshot.json.gz`).
