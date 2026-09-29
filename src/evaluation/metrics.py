"""
Canonical Evaluation Metrics Library — StandSpec AI (Phase P1-D)
Single authoritative source of truth for recommendation and retrieval metrics.
Eliminates duplicated or inconsistent Top-1 definitions across evaluation and ablation scripts.

Definitions:
1. RAW_RETRIEVAL_TOP1:
   - Numerator: Queries where the first candidate from retrieval (pre-applicability) matches gold.
   - Denominator: Evaluated queries.
   - Review candidate counts: No.
2. EFFECTIVE_CANDIDATE_TOP1:
   - Numerator: Queries where the highest-ranked viable candidate (verified primary OR review candidate) matches gold.
   - Denominator: Evaluated queries.
   - Review candidate counts: Yes.
3. VERIFIED_PRIMARY_TOP1:
   - Numerator: Queries where a primary recommendation was issued AND matches gold.
   - Denominator: Evaluated queries.
   - Review candidate counts: No (unverified candidates are not recommendations).
"""

from typing import List, Dict, Any, Optional, Set
import math


def compute_raw_retrieval_top1(queries: List[Dict[str, Any]], outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes RAW_RETRIEVAL_TOP1.
    Population: All evaluated queries with gold standards.
    Numerator: Top candidate from retrieval channel matches gold standard.
    """
    matches = 0
    total = 0
    for q, out in zip(queries, outputs):
        golds = {g.get("standard_designation") for g in q.get("gold_standards", [])}
        if not golds:
            continue
        total += 1
        raw_cands = out.get("candidate_recommendations") or out.get("fused_candidates") or []
        if raw_cands:
            top_desig = raw_cands[0].get("standard_designation") or raw_cands[0].get("designation")
            if top_desig in golds:
                matches += 1

    rate = round(matches / total, 4) if total > 0 else 0.0
    return {
        "metric_name": "RAW_RETRIEVAL_TOP1",
        "numerator": matches,
        "denominator": total,
        "value": rate,
        "percentage": round(rate * 100, 2),
        "review_candidates_counted": False,
    }


def compute_effective_candidate_top1(queries: List[Dict[str, Any]], outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes EFFECTIVE_CANDIDATE_TOP1.
    Population: All evaluated queries with gold standards.
    Numerator: Top candidate (verified primary OR review candidate) matches gold.
    """
    matches = 0
    total = 0
    for q, out in zip(queries, outputs):
        golds = {g.get("standard_designation") for g in q.get("gold_standards", [])}
        if not golds:
            continue
        total += 1
        primary = out.get("primary_recommendation")
        review = out.get("review_candidate")
        top_desig = (primary.get("standard_designation") if primary else None) or (
            review.get("standard_designation") if review else None
        )
        if top_desig and top_desig in golds:
            matches += 1

    rate = round(matches / total, 4) if total > 0 else 0.0
    return {
        "metric_name": "EFFECTIVE_CANDIDATE_TOP1",
        "numerator": matches,
        "denominator": total,
        "value": rate,
        "percentage": round(rate * 100, 2),
        "review_candidates_counted": True,
    }


def compute_verified_primary_top1(queries: List[Dict[str, Any]], outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes VERIFIED_PRIMARY_TOP1.
    Population: All evaluated queries.
    Numerator: Primary recommendation is issued AND matches gold.
    """
    matches = 0
    total = 0
    for q, out in zip(queries, outputs):
        golds = {g.get("standard_designation") for g in q.get("gold_standards", [])}
        total += 1
        primary = out.get("primary_recommendation")
        if primary and primary.get("standard_designation") in golds:
            matches += 1

    rate = round(matches / total, 4) if total > 0 else 0.0
    return {
        "metric_name": "VERIFIED_PRIMARY_TOP1",
        "numerator": matches,
        "denominator": total,
        "value": rate,
        "percentage": round(rate * 100, 2),
        "review_candidates_counted": False,
    }


def compute_recall_at_k(queries: List[Dict[str, Any]], outputs: List[Dict[str, Any]], k: int = 5) -> Dict[str, Any]:
    """
    Computes Recall@k.
    Population: Queries with gold standards.
    Numerator: At least one gold standard appears in the top-k candidate list.
    """
    hits = 0
    total = 0
    for q, out in zip(queries, outputs):
        golds = {g.get("standard_designation") for g in q.get("gold_standards", [])}
        if not golds:
            continue
        total += 1
        cands = [
            c.get("standard_designation") or c.get("designation")
            for c in out.get("candidate_recommendations", [])
        ]
        rev = out.get("review_candidate")
        if rev and rev.get("standard_designation") not in cands:
            cands.insert(0, rev.get("standard_designation"))
        prim = out.get("primary_recommendation")
        if prim and prim.get("standard_designation") not in cands:
            cands.insert(0, prim.get("standard_designation"))

        if any(c in golds for c in cands[:k]):
            hits += 1

    rate = round(hits / total, 4) if total > 0 else 0.0
    return {
        "metric_name": f"RECALL_AT_{k}",
        "k": k,
        "numerator": hits,
        "denominator": total,
        "value": rate,
        "percentage": round(rate * 100, 2),
    }


def compute_mrr(queries: List[Dict[str, Any]], outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes Mean Reciprocal Rank (MRR).
    Population: Queries with gold standards.
    Reciprocal rank of first matching gold standard in candidate pool.
    """
    rr_sum = 0.0
    total = 0
    for q, out in zip(queries, outputs):
        golds = {g.get("standard_designation") for g in q.get("gold_standards", [])}
        if not golds:
            continue
        total += 1
        cands = [
            c.get("standard_designation") or c.get("designation")
            for c in out.get("candidate_recommendations", [])
        ]
        rev = out.get("review_candidate")
        if rev and rev.get("standard_designation") not in cands:
            cands.insert(0, rev.get("standard_designation"))
        prim = out.get("primary_recommendation")
        if prim and prim.get("standard_designation") not in cands:
            cands.insert(0, prim.get("standard_designation"))

        rr = 0.0
        for rank, c in enumerate(cands, 1):
            if c in golds:
                rr = 1.0 / rank
                break
        rr_sum += rr

    mrr = round(rr_sum / total, 4) if total > 0 else 0.0
    return {
        "metric_name": "MRR",
        "value": mrr,
        "denominator": total,
    }


def is_primary_unsupported(primary: Dict[str, Any]) -> bool:
    """Checks if primary recommendation lacks required evidentiary support."""
    bundle = primary.get("evidence_bundle") or {}
    if not bundle:
        has_scope = bool((primary.get("scope") or "").strip())
        has_prov = bool(primary.get("provenance") or primary.get("source_department"))
        return not (has_scope and has_prov)
    
    scope_ready = bundle.get("scope_ready", False)
    applicability_ready = bundle.get("applicability_ready", False)
    lifecycle_ready = bundle.get("lifecycle_ready", False)
    provenance_ready = bundle.get("provenance_ready", False)
    return not (scope_ready and applicability_ready and lifecycle_ready and provenance_ready)


def is_primary_wrong_role(primary: Dict[str, Any]) -> bool:
    """Checks if primary recommendation has incompatible semantic role."""
    role = (primary.get("evidence_bundle") or {}).get("standard_role") or primary.get("standard_role") or ""
    incompatible = {
        "TEST_METHOD",
        "TERMINOLOGY",
        "DIMENSIONAL_MOUNTING",
        "CODE_OF_PRACTICE",
        "GUIDELINES",
        "SUPPORTING_STANDARD",
        "COMPONENT",
        "EXTERNAL_STANDARD",
    }
    return role in incompatible


def is_primary_wrong_edition(primary: Dict[str, Any]) -> bool:
    """Checks if primary recommendation selects an edition not allowed by lifecycle contract."""
    lifecycle = primary.get("lifecycle") or (primary.get("evidence_bundle") or {}).get("lifecycle") or {}
    if lifecycle.get("is_superseded") is True:
        return True
    status = str((lifecycle.get("status") or lifecycle.get("lifecycle_state") or "")).upper()
    return status in ("SUPERSEDED", "WITHDRAWN", "CANCELLED", "INACTIVE")


def compute_safety_metrics(queries: List[Dict[str, Any]], outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes Authoritative Trust and Safety metrics (Phase P1-E):
    - wrong_primary_promotion_rate: Emits primary not matching gold set for in-scope queries.
    - unsupported_primary_promotion_rate: Primary lacks evidentiary readiness.
    - wrong_role_primary_rate: Primary recommendation has incompatible role.
    - wrong_part_primary_rate: Primary selects wrong part/section family.
    - wrong_edition_primary_rate: Primary selects superseded or unverified edition.
    - regulatory_false_assertion_rate: System misasserts regulatory mandate against gold.
    - safe_primary_rate: Primary meets all correctness, role, evidence, and lifecycle criteria.
    - unsafe_primary_rate: Composite rate of queries emitting any unsafe primary recommendation.
    - safe_decision_accuracy: Engine makes the correct safe recommendation or abstention.
    - safe_abstention_rate: Abstains when gold is unready or missing.
    - hard_negative_rejection_rate: Rejects hard negatives at top-1.
    - hard_negative_intrusion_rate_5: Prevents hard negatives in top-5.
    - coverage_detection_accuracy: Correctly identifies out-of-coverage queries.
    """
    total = len(queries)
    if total == 0:
        return {}

    safe_decisions = 0
    unsafe_primaries = 0
    safe_abstentions = 0
    abstention_opportunities = 0

    total_primaries = 0
    safe_primaries = 0
    unsupported_primaries = 0
    wrong_role_primaries = 0
    wrong_edition_primaries = 0
    supporting_as_primary = 0

    in_scope_with_gold_queries = 0
    wrong_primaries_in_scope = 0
    wrong_part_primaries = 0

    regulatory_eval_queries = 0
    regulatory_false_assertions = 0

    total_hn_queries = 0
    hn_rejected_at1 = 0
    hn_intrusions_5 = 0

    outside_queries = 0
    outside_detected = 0

    for q, out in zip(queries, outputs):
        golds = {g.get("standard_designation") for g in q.get("gold_standards", []) if g.get("standard_designation")}
        gold_bases = {str(g.get("base_number")) for g in q.get("gold_standards", []) if g.get("base_number")}
        hns = {h.get("standard_designation") for h in q.get("hard_negatives", []) if h.get("standard_designation")}
        cov_state = q.get("expected_coverage_state", "IN_PROTOTYPE_COVERAGE")
        exp_decision = q.get("expected_decision", {}).get("query_level_state")

        primary = out.get("primary_recommendation")
        review = out.get("review_candidate")
        decision_state = out.get("decision_state")

        # 1. Coverage Detection
        if cov_state != "IN_PROTOTYPE_COVERAGE":
            outside_queries += 1
            if decision_state in ("OUTSIDE_PROTOTYPE_COVERAGE", "NO_CONFIDENT_MATCH"):
                outside_detected += 1

        # 2. Hard Negatives
        if hns:
            total_hn_queries += 1
            top_cand = (primary.get("standard_designation") if primary else None) or (
                review.get("standard_designation") if review else None
            )
            if top_cand not in hns:
                hn_rejected_at1 += 1
            
            cands = [c.get("standard_designation") for c in out.get("candidate_recommendations", [])]
            if any(c in hns for c in cands[:5]):
                hn_intrusions_5 += 1

        # Track in-scope with gold
        is_in_scope_with_gold = (cov_state == "IN_PROTOTYPE_COVERAGE" and len(golds) > 0)
        if is_in_scope_with_gold:
            in_scope_with_gold_queries += 1

        # 3. Primary Recommendation Evaluation
        if primary:
            total_primaries += 1
            desig = primary.get("standard_designation")
            base_num = str(primary.get("base_number") or (primary.get("evidence_bundle") or {}).get("base_number") or "")

            is_wrong_primary = False
            if is_in_scope_with_gold and (desig not in golds):
                is_wrong_primary = True
                wrong_primaries_in_scope += 1
            elif not is_in_scope_with_gold and cov_state != "IN_PROTOTYPE_COVERAGE":
                is_wrong_primary = True

            # Wrong Part check (base matches but specific part doesn't)
            if golds and (desig not in golds) and (base_num and base_num in gold_bases):
                wrong_part_primaries += 1

            unsupported = is_primary_unsupported(primary)
            if unsupported:
                unsupported_primaries += 1

            wrong_role = is_primary_wrong_role(primary)
            if wrong_role:
                wrong_role_primaries += 1

            role = (primary.get("evidence_bundle") or {}).get("standard_role") or primary.get("standard_role")
            if role in ("SUPPORTING_STANDARD", "COMPONENT"):
                supporting_as_primary += 1

            wrong_edition = is_primary_wrong_edition(primary)
            if wrong_edition:
                wrong_edition_primaries += 1

            is_safe_primary = (
                (desig in golds) and
                not unsupported and
                not wrong_role and
                not wrong_edition and
                (desig not in hns) and
                (cov_state == "IN_PROTOTYPE_COVERAGE") and
                (decision_state == "PRIMARY_RECOMMENDATION_AVAILABLE")
            )
            if is_safe_primary:
                safe_primaries += 1

            # Any unsafe primary (wrong, unsupported, wrong role, superseded, or HN)
            if is_wrong_primary or unsupported or wrong_role or wrong_edition or (desig in hns):
                unsafe_primaries += 1

        # 4. Regulatory Assertion Tracking
        expected_reg = q.get("expected_regulatory_status") or q.get("regulatory_mandate_expected")
        if expected_reg in ("MANDATORY", "NON_MANDATORY"):
            regulatory_eval_queries += 1
            rec_for_reg = primary or review
            reg_status = (rec_for_reg.get("regulatory") or {}).get("regulatory_state") if rec_for_reg else None
            if expected_reg == "MANDATORY" and reg_status != "MANDATORY_CONFIRMED":
                regulatory_false_assertions += 1
            elif expected_reg == "NON_MANDATORY" and reg_status == "MANDATORY_CONFIRMED":
                regulatory_false_assertions += 1

        # 5. Safe Abstention / Overall Safe Decision Accuracy
        is_safe_decision = False
        if primary and (primary.get("standard_designation") in golds) and (decision_state == "PRIMARY_RECOMMENDATION_AVAILABLE"):
            is_safe_decision = True
        elif not primary:
            # System abstained
            if not golds or exp_decision in ("EXPERT_REVIEW_REQUIRED", "INSUFFICIENT_INFORMATION", "NO_CONFIDENT_MATCH", "OUTSIDE_PROTOTYPE_COVERAGE"):
                is_safe_decision = True
                safe_abstentions += 1
            elif review and (review.get("standard_designation") in golds):
                is_safe_decision = True
                safe_abstentions += 1

        if not golds or exp_decision in ("EXPERT_REVIEW_REQUIRED", "INSUFFICIENT_INFORMATION", "NO_CONFIDENT_MATCH", "OUTSIDE_PROTOTYPE_COVERAGE"):
            abstention_opportunities += 1

        if is_safe_decision:
            safe_decisions += 1

    return {
        "safe_decision_accuracy": round(safe_decisions / total, 4),
        "wrong_primary_promotion_rate": round(wrong_primaries_in_scope / in_scope_with_gold_queries, 4) if in_scope_with_gold_queries > 0 else 0.0,
        "unsupported_primary_promotion_rate": round(unsupported_primaries / total_primaries, 4) if total_primaries > 0 else 0.0,
        "wrong_role_primary_rate": round(wrong_role_primaries / total_primaries, 4) if total_primaries > 0 else 0.0,
        "wrong_part_primary_rate": round(wrong_part_primaries / total_primaries, 4) if total_primaries > 0 else 0.0,
        "wrong_edition_primary_rate": round(wrong_edition_primaries / total_primaries, 4) if total_primaries > 0 else 0.0,
        "regulatory_false_assertion_rate": round(regulatory_false_assertions / regulatory_eval_queries, 4) if regulatory_eval_queries > 0 else 0.0,
        "safe_primary_rate": round(safe_primaries / total_primaries, 4) if total_primaries > 0 else 1.0,
        "unsafe_primary_rate": round(unsafe_primaries / total, 4),
        "safe_abstention_rate": round(safe_abstentions / abstention_opportunities, 4) if abstention_opportunities > 0 else 1.0,
        "hard_negative_rejection_rate": round(hn_rejected_at1 / total_hn_queries, 4) if total_hn_queries > 0 else 1.0,
        "hard_negative_intrusion_rate_5": round(hn_intrusions_5 / total_hn_queries, 4) if total_hn_queries > 0 else 0.0,
        "supporting_as_primary_rate": round(supporting_as_primary / total_primaries, 4) if total_primaries > 0 else 0.0,
        "coverage_detection_accuracy": round(outside_detected / outside_queries, 4) if outside_queries > 0 else 1.0,
        "total_primaries_emitted": total_primaries,
        "in_scope_with_gold_queries": in_scope_with_gold_queries,
    }


def compute_comprehensive_metrics(queries: List[Dict[str, Any]], outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes all standard StandSpec metrics using the single shared implementation.
    """
    res = {}
    res["RAW_RETRIEVAL_TOP1"] = compute_raw_retrieval_top1(queries, outputs)
    res["EFFECTIVE_CANDIDATE_TOP1"] = compute_effective_candidate_top1(queries, outputs)
    res["VERIFIED_PRIMARY_TOP1"] = compute_verified_primary_top1(queries, outputs)
    res["recall_at_5"] = compute_recall_at_k(queries, outputs, k=5)
    res["recall_at_10"] = compute_recall_at_k(queries, outputs, k=10)
    res["mrr"] = compute_mrr(queries, outputs)
    res["safety_metrics"] = compute_safety_metrics(queries, outputs)
    return res
