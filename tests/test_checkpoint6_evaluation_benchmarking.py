"""
Regression Tests for Checkpoint 6: Evaluation / Benchmarking Hardening
PS 26108 Phases 14-15.

Phase 14: Evaluation Harness Hardening (Benchmark Result Validator)
Phase 15: Benchmark Integrity (Gold Standard Quality + Decision State Distribution)
"""

import pytest
from src.evaluation.benchmark_validator import (
    validate_metric_bounds,
    validate_numerator_denominator,
    validate_metric_ordering,
    validate_population_accounting,
    validate_safety_coherence,
    validate_benchmark_results,
    BenchmarkViolation,
    BenchmarkValidationResult,
)
from src.evaluation.benchmark_integrity import (
    validate_gold_standards,
    analyze_decision_state_distribution,
    analyze_error_taxonomy_coverage,
    compute_confidence_interval,
    generate_benchmark_integrity_report,
    GoldStandardIssue,
)


# ============================================================================
# Phase 14: Benchmark Result Validator
# ============================================================================

class TestMetricBounds:
    """Tests for CHECK-1: Metric bounds validation."""

    def test_valid_metrics_pass(self):
        metrics = {
            "RAW_RETRIEVAL_TOP1": {"value": 0.75},
            "EFFECTIVE_CANDIDATE_TOP1": {"value": 0.80},
            "VERIFIED_PRIMARY_TOP1": {"value": 0.65},
            "safety_metrics": {
                "safe_decision_accuracy": 0.85,
                "wrong_primary_promotion_rate": 0.05,
            },
        }
        violations = validate_metric_bounds(metrics)
        assert len(violations) == 0

    def test_out_of_bounds_detected(self):
        metrics = {
            "RAW_RETRIEVAL_TOP1": {"value": 1.5},  # > 1.0
        }
        violations = validate_metric_bounds(metrics)
        assert len(violations) > 0
        assert violations[0].check_id == "CHECK-1-BOUNDS"

    def test_negative_rate_detected(self):
        metrics = {
            "safety_metrics": {"safe_decision_accuracy": -0.1},
        }
        violations = validate_metric_bounds(metrics)
        assert len(violations) > 0

    def test_zero_and_one_pass(self):
        """Edge values 0.0 and 1.0 must pass."""
        metrics = {
            "RAW_RETRIEVAL_TOP1": {"value": 0.0},
            "EFFECTIVE_CANDIDATE_TOP1": {"value": 1.0},
            "safety_metrics": {},
        }
        violations = validate_metric_bounds(metrics)
        assert len(violations) == 0


class TestNumeratorDenominator:
    """Tests for CHECK-2: Numerator ≤ denominator."""

    def test_valid_counts_pass(self):
        metrics = {
            "RAW_RETRIEVAL_TOP1": {"numerator": 15, "denominator": 30},
        }
        violations = validate_numerator_denominator(metrics)
        assert len(violations) == 0

    def test_numerator_exceeds_denominator_fails(self):
        metrics = {
            "RAW_RETRIEVAL_TOP1": {"numerator": 35, "denominator": 30},
        }
        violations = validate_numerator_denominator(metrics)
        assert len(violations) > 0

    def test_equal_counts_pass(self):
        metrics = {
            "VERIFIED_PRIMARY_TOP1": {"numerator": 30, "denominator": 30},
        }
        violations = validate_numerator_denominator(metrics)
        assert len(violations) == 0


class TestMetricOrdering:
    """Tests for CHECK-3: Cross-metric ordering invariant."""

    def test_valid_ordering_passes(self):
        metrics = {
            "RAW_RETRIEVAL_TOP1": {"value": 0.80},
            "EFFECTIVE_CANDIDATE_TOP1": {"value": 0.75},
            "VERIFIED_PRIMARY_TOP1": {"value": 0.65},
        }
        violations = validate_metric_ordering(metrics)
        assert len(violations) == 0

    def test_verified_exceeds_effective_fails(self):
        """Verified > Effective is always an error."""
        metrics = {
            "RAW_RETRIEVAL_TOP1": {"value": 0.80},
            "EFFECTIVE_CANDIDATE_TOP1": {"value": 0.65},
            "VERIFIED_PRIMARY_TOP1": {"value": 0.70},
        }
        violations = validate_metric_ordering(metrics)
        assert any(v.severity == "ERROR" for v in violations)

    def test_equal_values_pass(self):
        metrics = {
            "RAW_RETRIEVAL_TOP1": {"value": 0.75},
            "EFFECTIVE_CANDIDATE_TOP1": {"value": 0.75},
            "VERIFIED_PRIMARY_TOP1": {"value": 0.75},
        }
        violations = validate_metric_ordering(metrics)
        assert len(violations) == 0


class TestPopulationAccounting:
    """Tests for CHECK-4: Population accounting."""

    def test_valid_population_passes(self):
        metrics = {
            "RAW_RETRIEVAL_TOP1": {"denominator": 30},
            "EFFECTIVE_CANDIDATE_TOP1": {"denominator": 30},
            "safety_metrics": {"in_scope_with_gold_queries": 25, "total_primaries": 20},
        }
        violations = validate_population_accounting(metrics, total_queries=30)
        assert len(violations) == 0

    def test_denominator_exceeds_total_fails(self):
        metrics = {
            "RAW_RETRIEVAL_TOP1": {"denominator": 50},
            "safety_metrics": {"total_primaries": 10},
        }
        violations = validate_population_accounting(metrics, total_queries=30)
        assert len(violations) > 0


class TestSafetyCoherence:
    """Tests for CHECK-5: Safety metric coherence."""

    def test_coherent_safety_passes(self):
        metrics = {
            "safety_metrics": {
                "safe_primaries_count": 15,
                "total_primaries": 20,
                "safe_abstentions_count": 8,
                "abstention_opportunities": 10,
            },
        }
        violations = validate_safety_coherence(metrics)
        assert len(violations) == 0

    def test_safe_exceeds_total_fails(self):
        metrics = {
            "safety_metrics": {
                "safe_primaries_count": 25,
                "total_primaries": 20,
                "safe_abstentions_count": 5,
                "abstention_opportunities": 10,
            },
        }
        violations = validate_safety_coherence(metrics)
        assert len(violations) > 0

    def test_abstention_exceeds_opportunities_fails(self):
        metrics = {
            "safety_metrics": {
                "safe_primaries_count": 10,
                "total_primaries": 20,
                "safe_abstentions_count": 15,
                "abstention_opportunities": 10,
            },
        }
        violations = validate_safety_coherence(metrics)
        assert len(violations) > 0


class TestFullBenchmarkValidation:
    """Tests for the complete validate_benchmark_results pipeline."""

    def test_valid_benchmark_passes(self):
        metrics = {
            "RAW_RETRIEVAL_TOP1": {"value": 0.80, "numerator": 24, "denominator": 30},
            "EFFECTIVE_CANDIDATE_TOP1": {"value": 0.75, "numerator": 22, "denominator": 30},
            "VERIFIED_PRIMARY_TOP1": {"value": 0.65, "numerator": 19, "denominator": 30},
            "safety_metrics": {
                "safe_decision_accuracy": 0.85,
                "wrong_primary_promotion_rate": 0.05,
                "safe_primaries_count": 18,
                "total_primaries": 20,
                "safe_abstentions_count": 8,
                "abstention_opportunities": 10,
            },
        }
        result = validate_benchmark_results(metrics, total_queries=30)
        assert result.is_valid is True
        assert result.error_count == 0

    def test_invalid_benchmark_fails(self):
        metrics = {
            "RAW_RETRIEVAL_TOP1": {"value": 1.5, "numerator": 45, "denominator": 30},
            "safety_metrics": {
                "safe_primaries_count": 50,
                "total_primaries": 20,
            },
        }
        result = validate_benchmark_results(metrics, total_queries=30)
        assert result.is_valid is False
        assert result.error_count > 0


# ============================================================================
# Phase 15: Benchmark Integrity
# ============================================================================

class TestGoldStandardValidation:
    """Tests for gold standard quality validation."""

    def test_valid_golds_pass(self):
        queries = [
            {
                "query_id": "Q1",
                "query": {"raw_text": "Supply of HDPE pipes"},
                "gold_standards": [{"standard_designation": "IS 4984:2016"}],
                "hard_negatives": [{"standard_designation": "IS 7634:1975"}],
            },
        ]
        issues = validate_gold_standards(queries)
        assert len([i for i in issues if i.severity == "ERROR"]) == 0

    def test_duplicate_query_id_detected(self):
        queries = [
            {"query_id": "Q1", "query": {"raw_text": "HDPE pipes"}, "gold_standards": [{"standard_designation": "IS 4984"}]},
            {"query_id": "Q1", "query": {"raw_text": "PVC cables"}, "gold_standards": [{"standard_designation": "IS 694"}]},
        ]
        issues = validate_gold_standards(queries)
        assert any(i.issue_type == "DUPLICATE_QUERY_ID" for i in issues)

    def test_missing_designation_detected(self):
        queries = [
            {
                "query_id": "Q1",
                "query": {"raw_text": "HDPE pipes"},
                "gold_standards": [{"standard_designation": ""}],
            },
        ]
        issues = validate_gold_standards(queries)
        assert any(i.issue_type == "MISSING_DESIGNATION" for i in issues)

    def test_gold_hard_negative_overlap_detected(self):
        queries = [
            {
                "query_id": "Q1",
                "query": {"raw_text": "HDPE pipes"},
                "gold_standards": [{"standard_designation": "IS 4984:2016"}],
                "hard_negatives": [{"standard_designation": "IS 4984:2016"}],
            },
        ]
        issues = validate_gold_standards(queries)
        assert any(i.issue_type == "GOLD_HARD_NEGATIVE_OVERLAP" for i in issues)

    def test_missing_query_text_detected(self):
        queries = [
            {
                "query_id": "Q1",
                "query": {"raw_text": ""},
                "gold_standards": [{"standard_designation": "IS 4984"}],
            },
        ]
        issues = validate_gold_standards(queries)
        assert any(i.issue_type == "MISSING_QUERY_TEXT" for i in issues)


class TestDecisionStateDistribution:
    """Tests for decision state distribution analysis."""

    def test_balanced_distribution(self):
        outputs = [
            {"decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE"},
            {"decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE"},
            {"decision_state": "EXPERT_REVIEW_REQUIRED"},
            {"decision_state": "NO_CONFIDENT_MATCH"},
        ]
        dist = analyze_decision_state_distribution(outputs)
        assert dist["total_outputs"] == 4
        assert dist["summary"]["positive_count"] == 2
        assert dist["summary"]["abstention_count"] == 1
        assert len(dist["warnings"]) == 0

    def test_full_abstention_warning(self):
        outputs = [
            {"decision_state": "NO_CONFIDENT_MATCH"},
            {"decision_state": "INSUFFICIENT_INFORMATION"},
            {"decision_state": "OUTSIDE_PROTOTYPE_COVERAGE"},
        ]
        dist = analyze_decision_state_distribution(outputs)
        assert any("FULL_ABSTENTION" in w for w in dist["warnings"])

    def test_zero_primary_warning(self):
        outputs = [
            {"decision_state": "EXPERT_REVIEW_REQUIRED"},
            {"decision_state": "NO_CONFIDENT_MATCH"},
        ]
        dist = analyze_decision_state_distribution(outputs)
        assert any("ZERO_PRIMARY" in w for w in dist["warnings"])


class TestErrorTaxonomyCoverage:
    """Tests for error taxonomy coverage analysis."""

    def test_coverage_analysis(self):
        error_labels = [
            ["RETRIEVAL_MISS", "RETRIEVAL_MISS_LEXICAL_GAP"],
            ["WRONG_PRIMARY", "RERANKING_MISS"],
            ["EXTRACTION_MISS", "PRODUCT_CATEGORY_MISS"],
            [],  # Unlabeled failure
        ]
        result = analyze_error_taxonomy_coverage(error_labels)
        assert result["total_labeled_failures"] == 3
        assert result["unlabeled_failures"] == 1
        assert result["used_labels_count"] == 6
        assert "RETRIEVAL_MISS" in result["label_distribution"]

    def test_empty_labels(self):
        result = analyze_error_taxonomy_coverage([])
        assert result["total_labeled_failures"] == 0
        assert result["unlabeled_failures"] == 0


class TestConfidenceIntervals:
    """Tests for Wilson score confidence intervals."""

    def test_perfect_rate(self):
        ci = compute_confidence_interval(100, 100)
        assert ci["center"] > 0.95
        assert ci["lower"] > 0.90
        assert ci["upper"] <= 1.0

    def test_zero_rate(self):
        ci = compute_confidence_interval(0, 100)
        assert ci["center"] < 0.05
        assert ci["lower"] >= 0.0

    def test_empty_population(self):
        ci = compute_confidence_interval(0, 0)
        assert ci["lower"] == 0.0
        assert ci["upper"] == 0.0
        assert ci["n"] == 0

    def test_small_sample(self):
        """Small samples should have wide intervals."""
        ci = compute_confidence_interval(3, 5)
        width = ci["upper"] - ci["lower"]
        assert width > 0.3  # Wide interval for n=5

    def test_large_sample(self):
        """Large samples should have narrow intervals."""
        ci = compute_confidence_interval(800, 1000)
        width = ci["upper"] - ci["lower"]
        assert width < 0.05  # Narrow interval for n=1000


class TestIntegrityReport:
    """Tests for the complete integrity report generator."""

    def test_report_structure(self):
        queries = [
            {
                "query_id": "Q1",
                "query": {"raw_text": "HDPE pipes"},
                "gold_standards": [{"standard_designation": "IS 4984:2016"}],
            },
        ]
        outputs = [
            {"decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE"},
        ]
        metrics = {
            "safety_metrics": {
                "safe_primaries_count": 1,
                "total_primaries": 1,
                "safe_abstentions_count": 0,
                "abstention_opportunities": 0,
            },
        }
        report = generate_benchmark_integrity_report(queries, outputs, metrics)
        assert "gold_standard_quality" in report
        assert "decision_state_distribution" in report
        assert "error_taxonomy_coverage" in report
        assert "confidence_intervals" in report
        assert report["gold_standard_quality"]["total_queries"] == 1
