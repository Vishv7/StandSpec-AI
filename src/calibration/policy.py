"""
Calibrated Selective Abstention Policy — StandSpec AI (Layer 5 Calibration)
Decides whether to recommend or abstain based on calibrated posterior probabilities,
confidence margins, technical applicability, and missing discriminators.

Phase 10 Enhancement: Evidence-aware abstention with structured reasons,
integration with discriminator policy, and abstention metadata.
"""

from typing import List, Dict, Any, Optional, Tuple
from src.calibration.calibrator import PlattScaler


class SelectiveAbstentionPolicy:
    """
    Calibrated Selective Abstention Policy.
    Enforces risk-coverage tradeoffs:
    High threshold -> Low risk (high accuracy on covered queries) with safe abstention on ambiguity.
    """

    def __init__(
        self,
        tau_recommend: float = 0.40,
        tau_min: float = 0.35,
        delta_margin: float = 0.04,
        calibrator: Optional[PlattScaler] = None,
        calibrator_path: Optional[str] = "data/models/calibrator_v1.json",
    ):
        self.tau_recommend = tau_recommend
        self.tau_min = tau_min
        self.delta_margin = delta_margin
        
        if calibrator is not None:
            self.calibrator = calibrator
            self.is_empirical_calibrator = True
        elif calibrator_path:
            from pathlib import Path
            p = Path(calibrator_path)
            if p.exists():
                try:
                    self.calibrator = PlattScaler.load(p)
                    self.is_empirical_calibrator = True
                except Exception:
                    self.calibrator = PlattScaler(a=3.0, b=-1.8)
                    self.is_empirical_calibrator = False
            else:
                self.calibrator = PlattScaler(a=3.0, b=-1.8)
                self.is_empirical_calibrator = False
        else:
            self.calibrator = PlattScaler(a=3.0, b=-1.8)
            self.is_empirical_calibrator = False

    def decide(
        self,
        applicable_recommendations: List[Dict[str, Any]],
        missing_discriminators: List[str] = None,
    ) -> Tuple[str, Optional[str], Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Evaluate candidates and return:
        (decision_state, abstention_reason, primary_rec, viable_recs)
        """
        missing_discriminators = missing_discriminators or []

        if not applicable_recommendations:
            return (
                "NO_CONFIDENT_MATCH",
                "No candidate standard achieved technical applicability and grounding.",
                None,
                [],
            )

        # Calibrate confidence scores
        calibrated_recs = []
        for r in applicable_recommendations:
            r_copy = dict(r)
            raw_score = r.get("confidence_score", 0.0)
            cal_prob = self.calibrator.predict_proba(raw_score)
            r_copy["calibrated_confidence"] = cal_prob
            calibrated_recs.append(r_copy)

        calibrated_recs.sort(key=lambda x: -x["calibrated_confidence"])

        top1 = calibrated_recs[0]
        top1_prob = top1["calibrated_confidence"]

        # Viable recommendations: meeting minimal confidence
        viable = [r for r in calibrated_recs if r["calibrated_confidence"] >= self.tau_min]

        if not viable or top1_prob < self.tau_min:
            return (
                "NO_CONFIDENT_MATCH",
                f"Top candidate calibrated confidence ({top1_prob:.2f}) falls below minimum confidence threshold ({self.tau_min:.2f}).",
                None,
                [],
            )

        # Insufficient information due to missing discriminators
        if missing_discriminators and len(viable) > 1:
            return (
                "INSUFFICIENT_INFORMATION",
                f"Missing critical discriminators: {', '.join(missing_discriminators)}. "
                "Multiple potential standards match the general description.",
                top1,
                viable,
            )

        # Ambiguity check: small score gap between top two distinct standards
        if len(viable) > 1:
            top2 = next(
                (
                    r for r in viable[1:]
                    if (r.get("standard_designation") or r.get("designation"))
                    != (top1.get("standard_designation") or top1.get("designation"))
                ),
                None,
            )
            if top2:
                top2_prob = top2["calibrated_confidence"]
                gap = abs(top1_prob - top2_prob)
                if gap < self.delta_margin and top1_prob < 0.72:
                    return (
                        "MULTIPLE_POSSIBLE_STANDARDS",
                        f"Top candidates have narrow calibrated probability margin ({gap:.3f} < {self.delta_margin:.3f}).",
                        top1,
                        viable,
                    )

        # Primary recommendation
        if top1_prob >= self.tau_recommend:
            return (
                "PRIMARY_RECOMMENDATION_AVAILABLE",
                None,
                top1,
                viable,
            )
        else:
            return (
                "NO_CONFIDENT_MATCH",
                f"Calibrated confidence ({top1_prob:.2f}) is below recommendation threshold ({self.tau_recommend:.2f}).",
                None,
                viable,
            )

    def build_abstention_metadata(
        self,
        decision_state: str,
        abstention_reason: Optional[str],
        primary_rec: Optional[Dict[str, Any]],
        viable_recs: List[Dict[str, Any]],
        missing_discriminators: Optional[List[str]] = None,
        evidence_gaps: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Build structured abstention metadata for any decision outcome.
        Phase 10: Provides structured, actionable abstention context.
        """
        is_abstention = decision_state in (
            "NO_CONFIDENT_MATCH", "INSUFFICIENT_INFORMATION",
            "OUTSIDE_PROTOTYPE_COVERAGE", "CONTRADICTORY_SPECIFICATIONS",
        )
        is_review = decision_state == "EXPERT_REVIEW_REQUIRED"
        is_conditional = decision_state == "CONDITIONAL_RECOMMENDATION"
        is_ambiguous = decision_state == "MULTIPLE_POSSIBLE_STANDARDS"

        metadata = {
            "decision_state": decision_state,
            "is_abstention": is_abstention,
            "is_review": is_review,
            "is_conditional": is_conditional,
            "is_ambiguous": is_ambiguous,
            "is_positive": decision_state == "PRIMARY_RECOMMENDATION_AVAILABLE",
            "abstention_reason": abstention_reason,
            "abstention_category": self._categorize_abstention(decision_state, abstention_reason),
            "user_actionable": self._generate_user_action(decision_state, missing_discriminators, evidence_gaps),
            "confidence_context": {
                "tau_recommend": self.tau_recommend,
                "tau_min": self.tau_min,
                "delta_margin": self.delta_margin,
                "top_candidate_confidence": primary_rec.get("calibrated_confidence") if primary_rec else None,
                "num_viable": len(viable_recs),
            },
            "missing_discriminators": missing_discriminators or [],
            "evidence_gaps": evidence_gaps or [],
        }

        return metadata

    def _categorize_abstention(
        self,
        decision_state: str,
        abstention_reason: Optional[str],
    ) -> str:
        """
        Categorize the abstention into a high-level category.
        Phase 10: Structured categories for UI rendering and analytics.
        """
        category_map = {
            "NO_CONFIDENT_MATCH": "CONFIDENCE_INSUFFICIENT",
            "INSUFFICIENT_INFORMATION": "QUERY_UNDERSPECIFIED",
            "OUTSIDE_PROTOTYPE_COVERAGE": "DOMAIN_OUT_OF_SCOPE",
            "CONTRADICTORY_SPECIFICATIONS": "QUERY_INVALID",
            "EXPERT_REVIEW_REQUIRED": "EVIDENCE_INSUFFICIENT",
            "MULTIPLE_POSSIBLE_STANDARDS": "AMBIGUOUS_MATCH",
            "CONDITIONAL_RECOMMENDATION": "PARTIAL_VERIFICATION",
            "PRIMARY_RECOMMENDATION_AVAILABLE": "NONE",
        }
        return category_map.get(decision_state, "UNKNOWN")

    def _generate_user_action(
        self,
        decision_state: str,
        missing_discriminators: Optional[List[str]] = None,
        evidence_gaps: Optional[List[str]] = None,
    ) -> str:
        """
        Generate an actionable suggestion for the user.
        Phase 10: Evidence-aware, specific suggestions.
        """
        if decision_state == "INSUFFICIENT_INFORMATION" and missing_discriminators:
            disc_list = ", ".join(missing_discriminators[:5])
            return f"Provide the following missing specifications: {disc_list}"

        if decision_state == "CONTRADICTORY_SPECIFICATIONS":
            return "Review and resolve the contradictory technical requirements in the tender specification."

        if decision_state == "OUTSIDE_PROTOTYPE_COVERAGE":
            return "This product category is outside the current system scope (CED + ETD divisions). Consult BIS directly."

        if decision_state == "EXPERT_REVIEW_REQUIRED" and evidence_gaps:
            gap_list = ", ".join(evidence_gaps[:5])
            return f"Expert review required due to: {gap_list}"

        if decision_state == "MULTIPLE_POSSIBLE_STANDARDS":
            return "Provide additional discriminating specifications (material, voltage class, grade, application) to narrow the match."

        if decision_state == "NO_CONFIDENT_MATCH":
            return "Refine the procurement query with more specific technical parameters or consult domain experts."

        return "Review the recommendation details."
