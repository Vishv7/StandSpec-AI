"""
Benchmark Integrity Analyzer — StandSpec AI (Phase 15, Checkpoint 6)
PS 26108 §16: Benchmark integrity and gold standard quality validation.

Validates:
  1. Gold standard completeness — required fields present
  2. Decision state distribution — all states accounted for
  3. Error taxonomy coverage — all failures classified
  4. Benchmark dataset quality — duplicates, missing fields, label noise
  5. Metric confidence intervals — statistical validity of reported metrics
"""

import math
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class GoldStandardIssue:
    """A quality issue with a gold standard entry."""
    query_id: str
    issue_type: str  # MISSING_DESIGNATION, MISSING_ROLE, DUPLICATE, etc.
    severity: str    # ERROR, WARNING, INFO
    message: str


def validate_gold_standards(queries: List[Dict[str, Any]]) -> List[GoldStandardIssue]:
    """
    Validate gold standard quality across the benchmark dataset.
    Checks for missing fields, duplicates, and structural issues.
    """
    issues = []
    seen_query_ids = set()
    seen_golds = Counter()

    for q in queries:
        qid = q.get("query_id", "UNKNOWN")

        # Check duplicate query IDs
        if qid in seen_query_ids:
            issues.append(GoldStandardIssue(
                query_id=qid,
                issue_type="DUPLICATE_QUERY_ID",
                severity="ERROR",
                message=f"Duplicate query_id: {qid}",
            ))
        seen_query_ids.add(qid)

        # Check query text
        raw_text = (q.get("query", {}) or {}).get("raw_text", "")
        if not raw_text.strip():
            issues.append(GoldStandardIssue(
                query_id=qid,
                issue_type="MISSING_QUERY_TEXT",
                severity="ERROR",
                message="Query has no raw_text",
            ))

        # Check gold standards
        golds = q.get("gold_standards", [])
        if not golds:
            # Some queries (out of domain, insufficient) legitimately have no golds
            cov = q.get("expected_coverage_state", "IN_PROTOTYPE_COVERAGE")
            if cov == "IN_PROTOTYPE_COVERAGE":
                issues.append(GoldStandardIssue(
                    query_id=qid,
                    issue_type="MISSING_GOLD_STANDARD",
                    severity="WARNING",
                    message="In-scope query has no gold standards",
                ))

        for g in golds:
            desig = g.get("standard_designation", "")
            if not desig:
                issues.append(GoldStandardIssue(
                    query_id=qid,
                    issue_type="MISSING_DESIGNATION",
                    severity="ERROR",
                    message="Gold standard entry missing standard_designation",
                ))
            else:
                seen_golds[desig] += 1

        # Check hard negatives don't overlap with golds
        hns = q.get("hard_negatives", [])
        gold_desigs = {g.get("standard_designation") for g in golds if g.get("standard_designation")}
        for hn in hns:
            hn_desig = hn.get("standard_designation", "")
            if hn_desig in gold_desigs:
                issues.append(GoldStandardIssue(
                    query_id=qid,
                    issue_type="GOLD_HARD_NEGATIVE_OVERLAP",
                    severity="ERROR",
                    message=f"Hard negative {hn_desig} also appears as gold standard",
                ))

    return issues


def analyze_decision_state_distribution(
    outputs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Analyze the distribution of decision states across benchmark outputs.
    Flags concerning distributions (e.g., 100% abstention, 0% primary).
    """
    state_counts = Counter()
    for out in outputs:
        state = out.get("decision_state", "UNKNOWN")
        state_counts[state] += 1

    total = len(outputs)
    distribution = {
        state: {"count": count, "percentage": round(count / total * 100, 1)}
        for state, count in state_counts.items()
    } if total > 0 else {}

    # Compute aggregate categories
    abstention_count = sum(
        state_counts.get(s, 0)
        for s in ("NO_CONFIDENT_MATCH", "INSUFFICIENT_INFORMATION",
                  "OUTSIDE_PROTOTYPE_COVERAGE", "CONTRADICTORY_SPECIFICATIONS")
    )
    positive_count = state_counts.get("PRIMARY_RECOMMENDATION_AVAILABLE", 0)
    review_count = state_counts.get("EXPERT_REVIEW_REQUIRED", 0)
    conditional_count = state_counts.get("CONDITIONAL_RECOMMENDATION", 0)

    warnings = []
    if total > 0:
        if positive_count == 0:
            warnings.append("ZERO_PRIMARY: No queries received a primary recommendation")
        if abstention_count == total:
            warnings.append("FULL_ABSTENTION: System abstained on every query")
        if positive_count == total:
            warnings.append("FULL_RECOMMENDATION: System recommended on every query — may indicate calibration issues")
        abstention_pct = abstention_count / total * 100
        if abstention_pct > 80:
            warnings.append(f"HIGH_ABSTENTION: {abstention_pct:.0f}% of queries resulted in abstention")

    return {
        "total_outputs": total,
        "distribution": distribution,
        "summary": {
            "positive_count": positive_count,
            "conditional_count": conditional_count,
            "review_count": review_count,
            "abstention_count": abstention_count,
            "positive_pct": round(positive_count / total * 100, 1) if total > 0 else 0.0,
            "abstention_pct": round(abstention_count / total * 100, 1) if total > 0 else 0.0,
        },
        "warnings": warnings,
    }


def analyze_error_taxonomy_coverage(
    error_labels: List[List[str]],
) -> Dict[str, Any]:
    """
    Analyze error taxonomy coverage across evaluation failures.
    Identifies which error labels appear and which are unused.
    """
    label_counts = Counter()
    unlabeled_count = 0
    total_failures = 0

    for labels in error_labels:
        if not labels:
            unlabeled_count += 1
        else:
            total_failures += 1
            for label in labels:
                label_counts[label] += 1

    # Known error labels (from the taxonomy)
    known_labels = {
        "EXTRACTION_MISS", "PRODUCT_CATEGORY_MISS", "MATERIAL_MISS",
        "APPLICATION_MISS", "MODIFIER_MISS", "PART_MISS", "SECTION_MISS",
        "EDITION_MISS", "ROLE_MISCLASSIFICATION", "PRIMARY_VS_SUPPORTING_ERROR",
        "RETRIEVAL_MISS", "RETRIEVAL_MISS_ABSENT_FROM_KB",
        "RETRIEVAL_MISS_UNHYDRATED_STUB", "RETRIEVAL_MISS_LEXICAL_GAP",
        "RETRIEVAL_MISS_SEMANTIC_GAP", "RETRIEVAL_MISS_BOTH_CHANNELS",
        "RETRIEVAL_LOW_FUSION_RANK", "RETRIEVAL_CROSS_ENCODER_DISPLACEMENT",
        "RETRIEVAL_GRAPH_EXPANSION_MISS",
        "RERANKING_MISS", "RERANKING_DISPLACEMENT",
        "APPLICABILITY_FALSE_REJECTION", "FALSE_ABSTENTION_THRESHOLD",
        "EVIDENCE_MISSING", "LIFECYCLE_UNVERIFIED", "REGULATORY_UNVERIFIED",
        "COVERAGE_OUTSIDE_DOMAIN", "QUERY_INSUFFICIENT", "CONTRADICTORY_QUERY",
        "KNOWN_HARD_NEGATIVE", "WRONG_PRIMARY", "WRONG_EDITION",
        "WRONG_ROLE", "WRONG_APPLICATION",
        "MATERIAL_FAMILY_MISMATCH", "PRODUCT_FAMILY_MISMATCH",
    }

    used_labels = set(label_counts.keys())
    unused_labels = known_labels - used_labels
    unknown_labels = used_labels - known_labels

    return {
        "total_labeled_failures": total_failures,
        "unlabeled_failures": unlabeled_count,
        "label_distribution": dict(label_counts.most_common()),
        "used_labels_count": len(used_labels),
        "unused_labels_count": len(unused_labels),
        "unused_labels": sorted(unused_labels),
        "unknown_labels": sorted(unknown_labels),
        "coverage_ratio": round(len(used_labels) / len(known_labels) * 100, 1) if known_labels else 0.0,
    }


def compute_confidence_interval(
    success_count: int,
    total_count: int,
    confidence_level: float = 0.95,
) -> Dict[str, float]:
    """
    Compute Wilson score confidence interval for a proportion.
    More robust than normal approximation for small sample sizes.
    """
    if total_count == 0:
        return {"lower": 0.0, "upper": 0.0, "center": 0.0, "n": 0}

    # Z-scores for common confidence levels
    z_map = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_map.get(confidence_level, 1.96)

    n = total_count
    p_hat = success_count / n

    denominator = 1 + z * z / n
    center = (p_hat + z * z / (2 * n)) / denominator
    spread = z * math.sqrt((p_hat * (1 - p_hat) + z * z / (4 * n)) / n) / denominator

    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)

    return {
        "lower": round(lower, 4),
        "upper": round(upper, 4),
        "center": round(center, 4),
        "n": n,
        "confidence_level": confidence_level,
    }


def generate_benchmark_integrity_report(
    queries: List[Dict[str, Any]],
    outputs: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    error_labels: Optional[List[List[str]]] = None,
) -> Dict[str, Any]:
    """
    Generate a comprehensive benchmark integrity report.
    """
    gold_issues = validate_gold_standards(queries)
    state_dist = analyze_decision_state_distribution(outputs)
    error_coverage = analyze_error_taxonomy_coverage(error_labels or [])

    # Confidence intervals for key metrics
    safety = metrics.get("safety_metrics", {})
    ci_primary = compute_confidence_interval(
        safety.get("safe_primaries_count", 0),
        safety.get("total_primaries", 0),
    )
    ci_abstention = compute_confidence_interval(
        safety.get("safe_abstentions_count", 0),
        safety.get("abstention_opportunities", 0),
    )

    return {
        "gold_standard_quality": {
            "total_queries": len(queries),
            "issue_count": len(gold_issues),
            "error_count": sum(1 for i in gold_issues if i.severity == "ERROR"),
            "warning_count": sum(1 for i in gold_issues if i.severity == "WARNING"),
            "issues": [
                {"query_id": i.query_id, "type": i.issue_type, "severity": i.severity, "message": i.message}
                for i in gold_issues[:20]  # Cap at 20 for readability
            ],
        },
        "decision_state_distribution": state_dist,
        "error_taxonomy_coverage": error_coverage,
        "confidence_intervals": {
            "safe_primary_rate": ci_primary,
            "safe_abstention_rate": ci_abstention,
        },
    }
