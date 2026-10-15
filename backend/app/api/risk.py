"""
Risk API: portfolio risk distribution, active component breakdowns, and weights documentation.
"""
from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends

from backend.app.api.posts import _ANALYZED_POSTS
from backend.app.core.security import verify_api_key

router = APIRouter(prefix="/api/risk", tags=["Risk Metrics"])

@router.get("", response_model=dict[str, Any])
async def get_risk_overview(api_key: str = Depends(verify_api_key)):
    """Returns real-time risk distribution across monitored streams."""
    level_counts = Counter({"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0})
    total_score_sum = 0

    for p in _ANALYZED_POSTS:
        risk_data = p.get("risk", {})
        lvl = risk_data.get("risk_level", "LOW")
        score = risk_data.get("total_score", 0)
        level_counts[lvl] += 1
        total_score_sum += score

    total_posts = len(_ANALYZED_POSTS)
    avg_score = round(total_score_sum / total_posts, 1) if total_posts > 0 else 0.0

    return {
        "average_risk_score": avg_score,
        "total_analyzed_posts": total_posts,
        "distribution": dict(level_counts),
        "methodology": {
            "formula": "Clamp[0..100](w_sev * Severity + w_ver * VerdictFactor + w_reach * Reach + w_vel * Velocity)",
            "weights_nominal": {"severity": 0.40, "verdict": 0.30, "reach": 0.15, "velocity": 0.15},
            "dynamic_renormalisation": "If engagement or timestamp metadata is missing, missing terms are dropped and remaining weights sum to 1.0.",
            "unvalidated_heuristic_notice": "Documented as unvalidated operational heuristic for bank prioritization.",
        }
    }
