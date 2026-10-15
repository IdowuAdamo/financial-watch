"""
Phase 1 Knowledge Base Ingestion Script.
Strictly conforms to ComplianceGate (RFC 9309, max(5s, crawl_delay), no header spoofing).
Probes download_list items, retries NDIC with backoff, and probes FactCheckHub/Dubawa.
"""
import asyncio
import json
import logging
import os

import httpx

from memory.compliance.gate import ComplianceGate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("phase1_ingestion")

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "registry", "sources.yaml")
RAW_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_store")
MANUAL_DIR = os.path.join(os.path.dirname(__file__), "..", "manual")

TARGET_ITEMS = [
    {
        "id": "cbn_heritage",
        "source_id": "cbn",
        "title": "CBN Revokes the Banking Licence of Heritage Bank Plc",
        "url": "https://www.cbn.gov.ng/Out/2024/CCD/CBN Press Release Heritage 030624.pdf",
        "publish_date": "2024-06-03",
        "suggested_file": "cbn_heritage_bank_revocation_2024.pdf",
    },
    {
        "id": "cbn_recapitalization",
        "source_id": "cbn",
        "title": "Review of Minimum Capital Requirements for Commercial, Merchant and Non-Interest",
        "url": "https://www.cbn.gov.ng/Out/2024/CCD/Recapitalization_MARCH_2024.pdf",
        "publish_date": "2024-03-28",
        "suggested_file": "cbn_minimum_capital_recapitalization_2024.pdf",
    },
    {
        "id": "cbn_bvn_no_expiry",
        "source_id": "cbn",
        "title": "Press Release: BVN Issued in Nigeria Has No Expiry Date - CBN",
        "url": "https://www.cbn.gov.ng/Out/2023/CCD/CBN Press Release BVN 100523.pdf",
        "publish_date": "2023-05-10",
        "suggested_file": "cbn_bvn_no_expiry_press_release.pdf",
    },
    {
        "id": "cbn_licensed_dmbs",
        "source_id": "cbn",
        "title": "List of Deposit Money Banks and Financial Holding Companies Operating in Nigeria",
        "url": "https://www.cbn.gov.ng/Out/2016/FPRD/DMBs Database 27-01-2016.pdf",
        "publish_date": "2024-01-01",
        "suggested_file": "cbn_licensed_deposit_money_banks.pdf",
    },
    {
        "id": "cbn_cybersecurity_withdrawal",
        "source_id": "cbn",
        "title": "Withdrawal Circular on Collection of National Cybersecurity Levy",
        "url": "https://www.cbn.gov.ng/Out/2024/CCD/WITHDRAWAL CIRCULAR ON CYBERSECURITY LEVY 17052024.pdf",
        "publish_date": "2024-05-17",
        "suggested_file": "cbn_withdrawal_cybersecurity_levy_circular.pdf",
    },
    {
        "id": "cbn_cybersecurity_alert",
        "source_id": "cbn",
        "title": "Press Release: CBN Alerts Public to Fraudulent Messages, Cyber Security Hack Attempts",
        "url": "https://www.cbn.gov.ng/Out/2026/CCD/Press Release on Cyber Security.pdf",
        "publish_date": "2026-03-01",
        "suggested_file": "cbn_fraud_and_cybersecurity_alert_2026.pdf",
    },
    {
        "id": "cbn_fraudulent_claims",
        "source_id": "cbn",
        "title": "Advisory on Fraudulent Claims and Fictitious Contracts Purportedly from the CBN",
        "url": "https://www.cbn.gov.ng/Out/2025/CCD/CBN Press Release 120525.pdf",
        "publish_date": "2025-05-12",
        "suggested_file": "cbn_fraudulent_contract_claims_advisory.pdf",
    },
    {
        "id": "cbn_beware_of_fraud",
        "source_id": "cbn",
        "title": "Beware of Fraudulent Loan Offers, Investment Schemes",
        "url": "https://www.cbn.gov.ng/Out/2020/CCD/bewareoffraud.pdf",
        "publish_date": "2020-04-01",
        "suggested_file": "cbn_fraudulent_loan_offers_advisory.pdf",
    },
    {
        "id": "cbn_tier1_wallets",
        "source_id": "cbn",
        "title": "Circular on Tier 1 Wallets & Accounts, Guidance Note and Profiling of Customers",
        "url": "https://www.cbn.gov.ng/Out/2023/PSMD/Circular on Tier 1 Wallets & Accounts, Guidance Note & Profiling of Customers' Accounts & Wallets.pdf",
        "publish_date": "2023-12-01",
        "suggested_file": "cbn_tier1_wallets_account_profiling.pdf",
    },
    {
        "id": "ndic_coverage",
        "source_id": "ndic",
        "title": "NDIC Press Release: Review of Maximum Deposit Insurance Coverage to N5,000,000 for Deposit Money Banks",
        "url": "https://ndic.gov.ng/press-release/",
        "publish_date": "2024-05-02",
        "suggested_file": "ndic_deposit_insurance_coverage_increase.html",
    },
    {
        "id": "africa_check_grant",
        "source_id": "africa_check",
        "title": "Africa Check: Viral Claim that CBN is Giving N50,000 Relief Funds or Grants",
        "url": "https://africacheck.org/fact-checks/reports/no-central-bank-nigeria-not-giving-n50000-grants-phishing-link",
        "publish_date": "2023-11-15",
        "suggested_file": "africacheck_cbn_fake_grants_investigation.html",
    },
]

async def probe_targets():
    os.makedirs(RAW_STORE_DIR, exist_ok=True)
    os.makedirs(MANUAL_DIR, exist_ok=True)

    gate = ComplianceGate(registry_path=REGISTRY_PATH)
    results = []

    async with httpx.AsyncClient(timeout=25.0) as client:
        for item in TARGET_ITEMS:
            logger.info(f"--- Probing Item: {item['title']} ---")
            source_id = item["source_id"]
            url = item["url"]

            # Retries for NDIC
            max_attempts = 3 if source_id == "ndic" else 1
            resp = None
            last_error = None

            for attempt in range(1, max_attempts + 1):
                try:
                    resp = await gate.fetch_url(client, source_id, url)
                    if resp is not None and resp.status_code == 200:
                        break
                    elif resp is not None:
                        last_error = f"HTTP {resp.status_code}"
                        break
                    else:
                        last_error = "Gate denied or fetch returned None"
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_attempts:
                        logger.info(f"Attempt {attempt} failed ({e}). Backing off 5s...")
                        await asyncio.sleep(5.0)

            if resp is not None and resp.status_code == 200:
                logger.info(f"SUCCESS: Fetched {len(resp.content)} bytes from {url}")
                # Save raw response
                save_filename = f"{item['id']}.bin"
                save_path = os.path.join(RAW_STORE_DIR, save_filename)
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                
                results.append({
                    "id": item["id"],
                    "title": item["title"],
                    "url": url,
                    "status": "SUCCESS",
                    "http_status": 200,
                    "content_length": len(resp.content),
                    "saved_to": save_path,
                    "publish_date": item["publish_date"],
                    "suggested_file": item["suggested_file"],
                })
            else:
                logger.warning(f"MANUAL ONLY: Could not fetch {url}: {last_error}")
                results.append({
                    "id": item["id"],
                    "title": item["title"],
                    "url": url,
                    "status": "MANUAL_ONLY",
                    "http_status": getattr(resp, "status_code", None),
                    "error": last_error,
                    "publish_date": item["publish_date"],
                    "suggested_file": item["suggested_file"],
                })

        # Also probe FactCheckHub sitemap and recent claims
        logger.info("--- Probing FactCheckHub sitemap ---")
        try:
            fch_resp = await gate.fetch_url(client, "factcheckhub", "https://factcheckhub.com/claim-checks/")
            if fch_resp and fch_resp.status_code == 200:
                logger.info(f"FactCheckHub claim-checks accessible: {len(fch_resp.content)} bytes")
                results.append({
                    "id": "factcheckhub_claims_index",
                    "title": "FactCheckHub Claim Checks Section",
                    "url": "https://factcheckhub.com/claim-checks/",
                    "status": "SUCCESS",
                    "http_status": 200,
                    "content_length": len(fch_resp.content),
                    "publish_date": "2026-10-15",
                    "suggested_file": "factcheckhub_claim_checks_index.html"
                })
        except Exception as e:
            logger.warning(f"FactCheckHub probe failed: {e}")

    # Write probe results
    out_path = os.path.join(MANUAL_DIR, "_probe_run_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Probe run results saved to {out_path}")
    return results

if __name__ == "__main__":
    asyncio.run(probe_targets())
