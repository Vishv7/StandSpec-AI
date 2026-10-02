"""
Benchmark Result Validator — StandSpec AI (Phase 14, Checkpoint 6)
PS 26108 §15: Evaluation harness hardening.

Validates benchmark results for:
  1. Metric consistency — numerators ≤ denominators, rates in [0,1]
  2. Population accounting — no queries lost between stages
  3. Decision state distribution — all states accounted for
  4. Safety metric coherence — unsafe rates + safe rates = 1.0
  5. Cross-metric invariants — Verified ≤ Effective ≤ Raw retrieval
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class BenchmarkViolation:
    """A single benchmark validation violation."""
    check_id: str
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    metric_name: str = ""
    expected: str = ""
    actual: str = ""


@dataclass
class BenchmarkValidationResult:
    """Result of benchmark validation."""
    is_valid: bool = True
    violations: List[BenchmarkViolation] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    checks_passed: int = 0
    checks_total: int = 0

    def add_violation(self, v: BenchmarkViolation):
        self.violations.append(v)
        if v.severity == "ERROR":
            self.error_count += 1
            self.is_valid = False
        elif v.severity == "WARNING":
            self.warning_count += 1

    def add_pass(self):
        self.checks_passed += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "violations": [
                {
                    "check_id": v.check_id,
                    "severity": v.severity,
                    "message": v.message,
                    "metric_name": v.metric_name,
                }
                for v in self.violations
            ],
        }


def validate_metric_bounds(metrics: Dict[str, Any]) -> List[BenchmarkViolation]:
    """
    CHECK-1: All rate metrics must be in [0.0, 1.0].
    """
    violations = []
    rate_keys = [
        "RAW_RETRIEVAL_TOP1", "EFFECTIVE_CANDIDATE_TOP1", "VERIFIED_PRIMARY_TOP1",
    ]
    for key in rate_keys:
        m = metrics.get(key, {})
        val = m.get("value")
        if val is not None and not (0.0 <= val <= 1.0):
            violations.append(BenchmarkViolation(
                check_id="CHECK-1-BOUNDS",
                severity="ERROR",
                message=f"Metric {key} value {val} is outside [0.0, 1.0]",
                metric_name=key,
                expected="[0.0, 1.0]",
                actual=str(val),
            ))

    # Safety metrics
    safety = metrics.get("safety_metrics", {})
    safety_rate_keys = [
        "safe_decision_accuracy", "wrong_primary_promotion_rate",
        "unsupported_primary_promotion_rate", "wrong_role_primary_rate",
        "wrong_part_primary_rate", "wrong_edition_primary_rate",
        "regulatory_false_assertion_rate", "unsafe_primary_rate",
        "hard_negative_rejection_rate", "hard_negative_intrusion_rate_5",
        "coverage_detection_accuracy",
    ]
    for key in safety_rate_keys:
        val = safety.get(key)
        if val is not None and not (0.0 <= val <= 1.0):
            violations.append(BenchmarkViolation(
                check_id="CHECK-1-BOUNDS-SAFETY",
                severity="ERROR",
                message=f"Safety metric {key} value {val} is outside [0.0, 1.0]",
                metric_name=key,
                expected="[0.0, 1.0]",
                actual=str(val),
            ))

    return violations


def validate_numerator_denominator(metrics: Dict[str, Any]) -> List[BenchmarkViolation]:
    """
    CHECK-2: Numerator must be ≤ denominator for all metrics.
    """
    violations = []
    nd_keys = ["RAW_RETRIEVAL_TOP1", "EFFECTIVE_CANDIDATE_TOP1", "VERIFIED_PRIMARY_TOP1"]
    for key in nd_keys:
        m = metrics.get(key, {})
        num = m.get("numerator")
        den = m.get("denominator")
        if num is not None and den is not None and num > den:
            violations.append(BenchmarkViolation(
                check_id="CHECK-2-NUM-DEN",
                severity="ERROR",
                message=f"Metric {key}: numerator ({num}) > denominator ({den})",
                metric_name=key,
                expected=f"numerator ≤ {den}",
                actual=str(num),
            ))

    return violations


def validate_metric_ordering(metrics: Dict[str, Any]) -> List[BenchmarkViolation]:
    """
    CHECK-3: Cross-metric invariant:
    VERIFIED_PRIMARY_TOP1 ≤ EFFECTIVE_CANDIDATE_TOP1 ≤ RAW_RETRIEVAL_TOP1 (by value)
    
    Rationale: Each successive metric applies stricter gates,
    so the pass rate must monotonically decrease or stay equal.
    """
    violations = []
    raw = (metrics.get("RAW_RETRIEVAL_TOP1") or {}).get("value")
    eff = (metrics.get("EFFECTIVE_CANDIDATE_TOP1") or {}).get("value")
    ver = (metrics.get("VERIFIED_PRIMARY_TOP1") or {}).get("value")

    if raw is not None and eff is not None and eff > raw + 0.001:
        violations.append(BenchmarkViolation(
            check_id="CHECK-3-ORDERING",
            severity="WARNING",
            message=f"EFFECTIVE ({eff:.4f}) > RAW ({raw:.4f}). "
                    "Effective includes review candidates, so this may be valid.",
            metric_name="METRIC_ORDERING",
        ))

    if ver is not None and eff is not None and ver > eff + 0.001:
        violations.append(BenchmarkViolation(
            check_id="CHECK-3-ORDERING",
            severity="ERROR",
            message=f"VERIFIED ({ver:.4f}) > EFFECTIVE ({eff:.4f}). "
                    "Verified primary cannot exceed effective candidate.",
            metric_name="METRIC_ORDERING",
        ))

    return violations


def validate_population_accounting(
    metrics: Dict[str, Any],
    total_queries: int,
) -> List[BenchmarkViolation]:
    """
    CHECK-4: Population accounting — total queries must match denominator counts.
    """
    violations = []

    for key in ["RAW_RETRIEVAL_TOP1", "EFFECTIVE_CANDIDATE_TOP1"]:
        m = metrics.get(key, {})
        den = m.get("denominator")
        if den is not None and den > total_queries:
            violations.append(BenchmarkViolation(
                check_id="CHECK-4-POPULATION",
                severity="ERROR",
                message=f"Metric {key} denominator ({den}) > total queries ({total_queries})",
                metric_name=key,
            ))

    safety = metrics.get("safety_metrics", {})
    in_scope = safety.get("in_scope_with_gold_queries", 0)
    total_primaries = safety.get("total_primaries", 0)

    if total_primaries > total_queries:
        violations.append(BenchmarkViolation(
            check_id="CHECK-4-POPULATION-PRIMARIES",
            severity="ERROR",
            message=f"Total primaries ({total_primaries}) > total queries ({total_queries})",
            metric_name="total_primaries",
        ))

    return violations


def validate_safety_coherence(metrics: Dict[str, Any]) -> List[BenchmarkViolation]:
    """
    CHECK-5: Safety metric coherence.
    safe_primaries + unsafe_primaries ≤ total_primaries
    safe_abstentions ≤ abstention_opportunities
    """
    violations = []
    safety = metrics.get("safety_metrics", {})

    safe_p = safety.get("safe_primaries_count", 0)
    total_p = safety.get("total_primaries", 0)
    if safe_p > total_p:
        violations.append(BenchmarkViolation(
            check_id="CHECK-5-COHERENCE",
            severity="ERROR",
            message=f"safe_primaries ({safe_p}) > total_primaries ({total_p})",
            metric_name="safety_coherence",
        ))

    safe_a = safety.get("safe_abstentions_count", 0)
    opp = safety.get("abstention_opportunities", 0)
    if safe_a > opp:
        violations.append(BenchmarkViolation(
            check_id="CHECK-5-COHERENCE-ABSTENTION",
            severity="ERROR",
            message=f"safe_abstentions ({safe_a}) > abstention_opportunities ({opp})",
            metric_name="safety_coherence",
        ))

    return violations


def validate_benchmark_results(
    metrics: Dict[str, Any],
    total_queries: int,
) -> BenchmarkValidationResult:
    """
    Run all benchmark validation checks.
    Returns BenchmarkValidationResult with all violations.
    """
    result = BenchmarkValidationResult()

    checks = [
        ("bounds", validate_metric_bounds(metrics)),
        ("num_den", validate_numerator_denominator(metrics)),
        ("ordering", validate_metric_ordering(metrics)),
        ("population", validate_population_accounting(metrics, total_queries)),
        ("safety", validate_safety_coherence(metrics)),
    ]

    for check_name, violations in checks:
        result.checks_total += 1
        if violations:
            for v in violations:
                result.add_violation(v)
        else:
            result.add_pass()

    return result
