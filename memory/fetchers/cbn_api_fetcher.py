"""
Fetches and archives official CBN document registry metadata from the internal API endpoint.
Endpoint: https://www.cbn.gov.ng/api/GetAllDocuments
NOTE: This endpoint is undocumented and unstable. It powers CBN's public Kendo UI document table.
All calls pass through the Compliance Gate once, saving raw JSON with SHA-256 and fetch timestamp.
"""
import asyncio
import hashlib
import json
import logging
import os
from datetime import UTC, datetime

import httpx

from memory.compliance.gate import ComplianceGate

logger = logging.getLogger("financial_watch.fetchers.cbn_api")

RAW_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_store")
ENDPOINT_URL = "https://www.cbn.gov.ng/api/GetAllDocuments"

async def fetch_cbn_metadata_once(force: bool = False) -> str:
    """
    Fetches CBN GetAllDocuments metadata ONCE through the compliance gate.
    Saves raw file with SHA-256 and retrieval timestamp.
    """
    os.makedirs(RAW_STORE_DIR, exist_ok=True)
    raw_path = os.path.join(RAW_STORE_DIR, "cbn_get_all_documents_raw.json")
    meta_path = os.path.join(RAW_STORE_DIR, "cbn_get_all_documents_raw.meta.json")

    if os.path.exists(raw_path) and not force:
        logger.info(f"Raw CBN metadata already exists at {raw_path}. Skipping refetch.")
        return raw_path

    gate = ComplianceGate()
    contact_url = os.getenv("CRAWLER_CONTACT_URL", "https://github.com/client/financial-watch")
    gate.contact_url = contact_url

    headers = {
        "User-Agent": f"FinancialWatchBot/1.0 (+{contact_url})",
        "Accept": "application/json, text/plain, */*",
    }

    logger.info(f"Fetching CBN metadata through compliance gate from {ENDPOINT_URL}...")
    
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        response = await gate.fetch_url(client, "cbn", ENDPOINT_URL)
        if response is None or response.status_code != 200:
            raise RuntimeError(f"Failed to fetch CBN metadata through ComplianceGate: HTTP {getattr(response, 'status_code', 'Blocked/Error')}")

        raw_bytes = response.content
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        retrieval_date = datetime.now(UTC).isoformat()

        # Save raw content
        with open(raw_path, "wb") as f:
            f.write(raw_bytes)

        # Parse count
        try:
            records = json.loads(raw_bytes.decode("utf-8"))
            record_count = len(records)
        except Exception:
            record_count = 0

        # Save metadata sidecar
        metadata = {
            "source_id": "cbn",
            "url": ENDPOINT_URL,
            "retrieval_date": retrieval_date,
            "sha256": sha256,
            "byte_size": len(raw_bytes),
            "record_count": record_count,
            "endpoint_stability_note": "Undocumented/unstable public API endpoint powering the CBN Kendo UI document table on cbn.gov.ng/Documents/allDocs.html.",
            "compliance_user_agent": headers["User-Agent"],
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        gate.log_decision("cbn", ENDPOINT_URL, "ALLOWED", f"Fetched {record_count} official records once. SHA-256: {sha256[:12]}...")
        logger.info(f"Successfully archived {record_count} CBN metadata records to {raw_path}")
        return raw_path

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(fetch_cbn_metadata_once())
