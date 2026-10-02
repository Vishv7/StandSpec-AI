"""
Canonical Error Taxonomy — StandSpec AI (Phase P1-E Section 20).
Defines standard labels and automated diagnostic classification for evaluation failures.
"""

from enum import Enum
from typing import Dict, Any, List, Set, Optional


class ErrorLabel(str, Enum):
    EXTRACTION_MISS = "EXTRACTION_MISS"
    PRODUCT_CATEGORY_MISS = "PRODUCT_CATEGORY_MISS"
    MATERIAL_MISS = "MATERIAL_MISS"
    APPLICATION_MISS = "APPLICATION_MISS"
    MODIFIER_MISS = "MODIFIER_MISS"
    PART_MISS = "PART_MISS"
    SECTION_MISS = "SECTION_MISS"
    EDITION_MISS = "EDITION_MISS"
    ROLE_MISCLASSIFICATION = "ROLE_MISCLASSIFICATION"
    PRIMARY_VS_SUPPORTING_ERROR = "PRIMARY_VS_SUPPORTING_ERROR"
    RETRIEVAL_MISS = "RETRIEVAL_MISS"
    RETRIEVAL_MISS_ABSENT_FROM_KB = "RETRIEVAL_MISS_ABSENT_FROM_KB"
    RETRIEVAL_MISS_UNHYDRATED_STUB = "RETRIEVAL_MISS_UNHYDRATED_STUB"
    RETRIEVAL_MISS_LEXICAL_GAP = "RETRIEVAL_MISS_LEXICAL_GAP"
    # Phase 7: Granular retrieval failure modes
    RETRIEVAL_MISS_SEMANTIC_GAP = "RETRIEVAL_MISS_SEMANTIC_GAP"
    RETRIEVAL_MISS_BOTH_CHANNELS = "RETRIEVAL_MISS_BOTH_CHANNELS"
    RETRIEVAL_LOW_FUSION_RANK = "RETRIEVAL_LOW_FUSION_RANK"
    RETRIEVAL_CROSS_ENCODER_DISPLACEMENT = "RETRIEVAL_CROSS_ENCODER_DISPLACEMENT"
    RETRIEVAL_GRAPH_EXPANSION_MISS = "RETRIEVAL_GRAPH_EXPANSION_MISS"
    RERANKING_MISS = "RERANKING_MISS"
    RERANKING_DISPLACEMENT = "RERANKING_DISPLACEMENT"
    APPLICABILITY_FALSE_REJECTION = "APPLICABILITY_FALSE_REJECTION"
    FALSE_ABSTENTION_THRESHOLD = "FALSE_ABSTENTION_THRESHOLD"
    EVIDENCE_MISSING = "EVIDENCE_MISSING"
    LIFECYCLE_UNVERIFIED = "LIFECYCLE_UNVERIFIED"
    REGULATORY_UNVERIFIED = "REGULATORY_UNVERIFIED"
    COVERAGE_OUTSIDE_DOMAIN = "COVERAGE_OUTSIDE_DOMAIN"
    QUERY_INSUFFICIENT = "QUERY_INSUFFICIENT"
    CONTRADICTORY_QUERY = "CONTRADICTORY_QUERY"
    KNOWN_HARD_NEGATIVE = "KNOWN_HARD_NEGATIVE"
    WRONG_PRIMARY = "WRONG_PRIMARY"
    WRONG_EDITION = "WRONG_EDITION"
    WRONG_ROLE = "WRONG_ROLE"
    WRONG_APPLICATION = "WRONG_APPLICATION"
    # Phase 7: Material/product mismatch labels
    MATERIAL_FAMILY_MISMATCH = "MATERIAL_FAMILY_MISMATCH"
    PRODUCT_FAMILY_MISMATCH = "PRODUCT_FAMILY_MISMATCH"


def classify_evaluation_error(
    query: Dict[str, Any],
    output: Dict[str, Any],
    graph: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Analyzes an evaluation failure and returns one or more canonical error labels.
    """
    labels: List[str] = []

    golds = {g.get("standard_designation") for g in query.get("gold_standards", []) if g.get("standard_designation")}
    gold_bases = {str(g.get("base_number")) for g in query.get("gold_standards", []) if g.get("base_number")}
    hns = {h.get("standard_designation") for h in query.get("hard_negatives", []) if h.get("standard_designation")}
    cov_state = query.get("expected_coverage_state", "IN_PROTOTYPE_COVERAGE")

    primary = output.get("primary_recommendation")
    review = output.get("review_candidate")
    candidates = output.get("candidate_recommendations", [])
    cand_desigs = [c.get("standard_designation") for c in candidates if c.get("standard_designation")]

    decision_state = output.get("decision_state")
    req_obj = output.get("normalized_requirements", {})
    reqs = req_obj.get("requirements", {})

    # 1. Coverage Outside Domain
    if cov_state != "IN_PROTOTYPE_COVERAGE":
        if decision_state not in ("OUTSIDE_PROTOTYPE_COVERAGE", "NO_CONFIDENT_MATCH"):
            labels.append(ErrorLabel.COVERAGE_OUTSIDE_DOMAIN.value)
        return labels

    # 2. Contradictory Query
    if req_obj.get("contradictions") or query.get("contradictions"):
        labels.append(ErrorLabel.CONTRADICTORY_QUERY.value)

    # 3. Query Insufficiency
    if decision_state == "INSUFFICIENT_INFORMATION":
        labels.append(ErrorLabel.QUERY_INSUFFICIENT.value)

    # 4. Extraction Checks
    if not reqs.get("product") or not (reqs.get("product") or {}).get("value"):
        labels.append(ErrorLabel.EXTRACTION_MISS.value)
        labels.append(ErrorLabel.PRODUCT_CATEGORY_MISS.value)

    # 5. Retrieval Miss vs Reranking Miss & Granular Root Causes
    if golds:
        gold_in_candidates = any(g in cand_desigs for g in golds)
        if not gold_in_candidates:
            labels.append(ErrorLabel.RETRIEVAL_MISS.value)
            if graph:
                for g in golds:
                    g_node = next((n for n in graph.get("nodes", []) if n.get("designation") == g), None)
                    if not g_node:
                        labels.append(ErrorLabel.RETRIEVAL_MISS_ABSENT_FROM_KB.value)
                    elif not (g_node.get("scope") or "").strip():
                        labels.append(ErrorLabel.RETRIEVAL_MISS_UNHYDRATED_STUB.value)
                    else:
                        labels.append(ErrorLabel.RETRIEVAL_MISS_LEXICAL_GAP.value)
        else:
            # Gold was retrieved, but not ranked top or not issued as primary
            top_cand = cand_desigs[0] if cand_desigs else None
            if top_cand and top_cand not in golds:
                labels.append(ErrorLabel.RERANKING_MISS.value)
                labels.append(ErrorLabel.RERANKING_DISPLACEMENT.value)
            if not primary:
                # Gold was retrieved in candidates, but no primary issued
                if decision_state in ("EXPERT_REVIEW_REQUIRED", "NO_CONFIDENT_MATCH"):
                    labels.append(ErrorLabel.FALSE_ABSTENTION_THRESHOLD.value)

    # 6. Wrong Primary Recommendation
    if primary:
        p_desig = primary.get("standard_designation")
        p_base = str(primary.get("base_number") or "")

        if golds and p_desig not in golds:
            labels.append(ErrorLabel.WRONG_PRIMARY.value)

            # Check if same base number (wrong part/section)
            if p_base and p_base in gold_bases:
                labels.append(ErrorLabel.PART_MISS.value)

        if p_desig in hns:
            labels.append(ErrorLabel.KNOWN_HARD_NEGATIVE.value)

        p_role = (primary.get("evidence_bundle") or {}).get("standard_role") or primary.get("standard_role")
        if p_role in ("TEST_METHOD", "TERMINOLOGY", "DIMENSIONAL_MOUNTING", "SUPPORTING_STANDARD", "COMPONENT"):
            labels.append(ErrorLabel.WRONG_ROLE.value)
            labels.append(ErrorLabel.ROLE_MISCLASSIFICATION.value)

        # Check edition
        lifecycle = primary.get("lifecycle") or (primary.get("evidence_bundle") or {}).get("lifecycle") or {}
        if lifecycle.get("is_superseded"):
            labels.append(ErrorLabel.WRONG_EDITION.value)
            labels.append(ErrorLabel.EDITION_MISS.value)

    # 7. Evidence Missing
    if review:
        missing_ev = review.get("missing_evidence") or review.get("evidence_gaps") or []
        if any("SCOPE" in str(e).upper() for e in missing_ev):
            labels.append(ErrorLabel.EVIDENCE_MISSING.value)

    # 8. Gold evidence availability in graph
    if graph and golds:
        for g_desig in golds:
            g_node = next((n for n in graph.get("nodes", []) if n.get("designation") == g_desig), None)
            if g_node and not (g_node.get("scope") or "").strip():
                if ErrorLabel.EVIDENCE_MISSING.value not in labels:
                    labels.append(ErrorLabel.EVIDENCE_MISSING.value)

    return list(dict.fromkeys(labels))  # Deduplicate preserving order
