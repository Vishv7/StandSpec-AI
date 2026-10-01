"""
Calibrated Selective Abstention Policy — StandSpec AI (Layer 5 Calibration)
Decides whether to recommend or abstain based on calibrated posterior probabilities,
confidence margins, technical applicability, and missing discriminators.
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
