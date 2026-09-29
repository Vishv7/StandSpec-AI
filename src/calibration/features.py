"""
Calibration Feature Extraction — StandSpec AI (Layer 5 Calibration)
Extracts grounding and confidence features from recommendation candidates
to feed into statistical calibration models (Platt scaling, Isotonic regression).
"""

from typing import Dict, Any, List, Optional
import math


class CalibrationFeatureExtractor:
    """
    Extracts calibration feature vectors from engine intermediate states.
    Features:
      0: raw_top_score
      1: score_gap (top1 - top2)
      2: product_matched (1.0 or 0.0)
      3: n_matched_attributes
      4: n_mismatched_attributes
      5: has_missing_discriminators (1.0 or 0.0)
      6: rank_agreement (1.0 if top candidate was also in top-3 BM25 & Dense)
    """

    def extract_features(
        self,
        candidate_recommendations: List[Dict[str, Any]],
        req_obj: Optional[Dict[str, Any]] = None,
        retrieval_candidates: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> List[float]:
        if not candidate_recommendations:
            return [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0]

        top1 = candidate_recommendations[0]
        top1_score = top1.get("confidence_score", 0.0)

        top2_score = 0.0
        if len(candidate_recommendations) > 1:
            top2_score = candidate_recommendations[1].get("confidence_score", 0.0)
        score_gap = max(0.0, top1_score - top2_score)

        app_info = top1.get("applicability", {})
        matched_attrs = app_info.get("matched_attributes", [])
        mismatched_attrs = app_info.get("mismatched_attributes", [])
        prod_matched = 1.0 if "PRODUCT" in matched_attrs or "product_scope_match" in matched_attrs else 0.0

        missing_disc = 0.0
        if req_obj and req_obj.get("missing_discriminators"):
            missing_disc = 1.0

        # Rank agreement
        rank_agreement = 0.0
        if retrieval_candidates:
            bm25_top3 = {c["designation"] for c in retrieval_candidates.get("bm25", [])[:3]}
            dense_top3 = {c["designation"] for c in retrieval_candidates.get("dense", [])[:3]}
            desig = top1.get("original_candidate") or top1.get("standard_designation")
            if desig in bm25_top3 and desig in dense_top3:
                rank_agreement = 1.0
            elif desig in bm25_top3 or desig in dense_top3:
                rank_agreement = 0.5

        return [
            float(top1_score),
            float(score_gap),
            float(prod_matched),
            float(len(matched_attrs)),
            float(len(mismatched_attrs)),
            float(missing_disc),
            float(rank_agreement),
        ]
