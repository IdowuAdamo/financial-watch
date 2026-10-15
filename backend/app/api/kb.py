"""
Knowledge Base Governance and Compliance Status API.
Returns registered source compliance statuses, robots.txt findings, rate limits, and database statistics.
"""
import os
from typing import Any

import yaml
from fastapi import APIRouter, Depends

from backend.app.core.security import verify_api_key
from memory.compliance.gate import ComplianceGate
from memory.store.db import KnowledgeBaseStore

router = APIRouter(prefix="/api/kb", tags=["Knowledge Base Governance"])

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "memory", "registry", "sources.yaml")
gate = ComplianceGate(registry_path=REGISTRY_PATH)

@router.get("/status", response_model=dict[str, Any])
async def get_kb_governance_status(api_key: str = Depends(verify_api_key)):
    """Returns source governance registry and database document counts."""
    # Load sources from YAML
    sources = []
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            sources = data.get("sources", [])

    store = KnowledgeBaseStore()
    try:
        db_stats = store.get_stats()
    except Exception as e:
        db_stats = {"error": f"Database offline: {e}"}

    audit_logs = gate.get_audit_logs(limit=25)

    return {
        "status": "healthy",
        "database_stats": db_stats,
        "sources": sources,
        "recent_compliance_logs": audit_logs,
        "crawler_user_agent": gate.robots_manager.get_full_user_agent(),
    }
