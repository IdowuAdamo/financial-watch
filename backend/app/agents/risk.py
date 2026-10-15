"""
Risk Agent.
Computes transparent, deterministic 0-100 reputational risk score.
Explicitly supports dynamic weight renormalisation when engagement or timestamp metadata is missing.
Documented as unvalidated heuristic scoring for operational prioritization.
"""
import math
from typing import Any

from backend.app.models.schemas import ClassificationResult, RiskScore, VerificationResult


class RiskAgent:
    """
    Computes mathematical risk score and details active scoring components.
    """
    @staticmethod
    def compute(
        narrative_cluster: dict[str, Any],
        verification: VerificationResult,
        classification: ClassificationResult,
        likes: int | None = None,
        shares: int | None = None,
        timestamp: str | None = None,
    ) -> RiskScore:
        # 1. Compute Base Severity (0-100)
        # Driven by the systemic impact of the topic
        base_severity = float(narrative_cluster.get("base_severity", 50))
        
        # 2. Compute Verdict Factor (0-100)
        if classification.category == "scam_impersonation":
            verdict_score = 95.0
        elif verification.verdict == "contradicted":
            verdict_score = 100.0 # Active misinformation has highest risk factor
        elif verification.verdict == "insufficient_evidence" or verification.verdict == "unverifiable":
            verdict_score = 55.0 # Cautionary ambiguity
        elif verification.verdict == "supported":
            verdict_score = 15.0 # Verified true announcement carries low misinformation risk
        else:
            verdict_score = 50.0

        # Base nominal weights
        w_severity = 0.40
        w_verdict = 0.30
        w_reach = 0.15
        w_velocity = 0.15

        active_components = ["Severity (Topic Impact)", "Verdict Factor (Verification Outcome)"]
        renormalised = False

        # 3. Reach Calculation (0-100)
        has_engagement = (likes is not None) or (shares is not None)
        reach_score = 0.0
        if has_engagement:
            total_eng = (likes or 0) + (shares or 0) * 3
            # Logarithmic scaling: 100 eng -> ~50 score, 10,000 eng -> ~95 score
            reach_score = min(100.0, max(0.0, math.log10(max(1, total_eng) + 1) * 25.0))
            active_components.append("Reach (Engagement Metric)")
        else:
            w_reach = 0.0
            renormalised = True

        # 4. Velocity Calculation (0-100)
        has_velocity = has_engagement and (timestamp is not None)
        velocity_score = 0.0
        if has_velocity:
            # Simulated velocity based on engagement density
            velocity_score = min(100.0, reach_score * 0.9)
            active_components.append("Velocity (Spread Acceleration)")
        else:
            w_velocity = 0.0
            renormalised = True

        # 5. Dynamic Renormalisation
        total_weight = w_severity + w_verdict + w_reach + w_velocity
        norm_w_severity = w_severity / total_weight
        norm_w_verdict = w_verdict / total_weight
        norm_w_reach = w_reach / total_weight if w_reach > 0 else 0.0
        norm_w_velocity = w_velocity / total_weight if w_velocity > 0 else 0.0

        total_score = (
            (norm_w_severity * base_severity) +
            (norm_w_verdict * verdict_score) +
            (norm_w_reach * reach_score) +
            (norm_w_velocity * velocity_score)
        )
        total_clamped = int(max(0, min(100, round(total_score))))

        # Determine level
        if total_clamped >= 80:
            level = "CRITICAL"
        elif total_clamped >= 60:
            level = "HIGH"
        elif total_clamped >= 35:
            level = "MEDIUM"
        else:
            level = "LOW"

        note = (
            "Heuristic weights dynamically renormalised (missing engagement/timestamp metadata)."
            if renormalised else
            "Full multi-factor weights applied (Severity + Verdict + Reach + Velocity)."
        )

        return RiskScore(
            total_score=total_clamped,
            risk_level=level,
            severity_score=round(base_severity, 1),
            velocity_score=round(velocity_score, 1),
            reach_score=round(reach_score, 1),
            verdict_score=round(verdict_score, 1),
            active_components=active_components,
            renormalised_note=note,
        )
