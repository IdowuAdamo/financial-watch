"""
Narrative Clustering Agent.
Clusters claims into evolving narrative threads and tracks estimated velocity and reach.
"""
from typing import Any

# Known narrative cluster archetypes in Nigerian banking
NARRATIVE_CLUSTERS = [
    {
        "id": "narr_insolvency_bank_run",
        "title": "Commercial Bank Insolvency & Run Panic",
        "keywords": ["distress", "withdraw", "bank run", "insolvent", "shut down", "fail"],
        "base_severity": 95,
    },
    {
        "id": "narr_fake_cbn_license_revocation",
        "title": "Fabricated CBN License Revocation Hoax",
        "keywords": ["revoke", "licence", "license", "cbn withdraws", "revoked"],
        "base_severity": 90,
    },
    {
        "id": "narr_credential_phishing",
        "title": "BVN & Account Suspension Phishing Scheme",
        "keywords": ["bvn", "otp", "pin", "suspended", "unblock", "link account"],
        "base_severity": 85,
    },
    {
        "id": "narr_recruitment_fraud",
        "title": "Unauthorized Recruitment & Interview Fee Scams",
        "keywords": ["recruitment", "interview fee", "job vacancy", "hiring form", "medical fee"],
        "base_severity": 70,
    },
    {
        "id": "narr_core_banking_outage",
        "title": "Digital Banking Interruption & Ledger Concerns",
        "keywords": ["app down", "maintenance", "upgrade", "ussd", "transaction failed", "cant transfer"],
        "base_severity": 45,
    },
]

class NarrativeAgent:
    @staticmethod
    def cluster(text: str, claims: list) -> dict[str, Any]:
        text_lower = text.lower()
        matched_cluster = None
        max_overlap = 0

        for cluster in NARRATIVE_CLUSTERS:
            overlap = sum(1 for kw in cluster["keywords"] if kw in text_lower)
            if overlap > max_overlap:
                max_overlap = overlap
                matched_cluster = cluster

        if not matched_cluster:
            matched_cluster = {
                "id": "narr_general_rumour",
                "title": "General Uncategorized Financial Rumour",
                "base_severity": 30,
            }

        return {
            "cluster_id": matched_cluster["id"],
            "cluster_title": matched_cluster["title"],
            "base_severity": matched_cluster["base_severity"],
        }
