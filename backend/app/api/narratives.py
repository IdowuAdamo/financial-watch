"""
Narratives API: aggregated cluster volume, velocity, and top themes.
"""
from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends

from backend.app.agents.narrative import NARRATIVE_CLUSTERS
from backend.app.api.posts import _ANALYZED_POSTS
from backend.app.core.security import verify_api_key

router = APIRouter(prefix="/api/narratives", tags=["Narratives & Clusters"])

@router.get("", response_model=list[dict[str, Any]])
async def get_narrative_clusters(api_key: str = Depends(verify_api_key)):
    """Returns aggregated narrative clusters and post counts."""
    # Count observed clusters
    counts = Counter()
    for p in _ANALYZED_POSTS:
        # Check trace step or claims
        for step in p.get("traces", []):
            if step.get("agent_name") == "Narrative Clustering Agent":
                cid = step.get("details", {}).get("cluster_id")
                if cid:
                    counts[cid] += 1

    results = []
    for cluster in NARRATIVE_CLUSTERS:
        cid = cluster["id"]
        count = counts.get(cid, 0)
        results.append({
            "cluster_id": cid,
            "title": cluster["title"],
            "base_severity": cluster["base_severity"],
            "post_count": count,
            "estimated_velocity": "High" if count >= 3 else "Moderate" if count >= 1 else "Low",
        })

    return results
