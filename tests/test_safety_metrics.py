"""
Tests for Authoritative Trust and Safety Metrics (Phase P1-E).
Verifies:
- WRONG_PRIMARY_PROMOTION_RATE
- UNSUPPORTED_PRIMARY_PROMOTION_RATE
- WRONG_ROLE_PRIMARY_RATE
- WRONG_PART_PRIMARY_RATE
- WRONG_EDITION_PRIMARY_RATE
- REGULATORY_FALSE_ASSERTION_RATE
- SAFE_PRIMARY_RATE
- Q_ADV_005 regression: A wrong verified primary must be flagged as wrong/unsafe.
"""

import pytest
from src.evaluation.metrics import (
    compute_safety_metrics,
    is_primary_unsupported,
    is_primary_wrong_role,
    is_primary_wrong_edition,
)


def test_q_adv_005_detected_as_wrong_primary():
    """
    Regression test for Section 1.3:
    In Q_ADV_005 ('Supply of uPVC pipes for agricultural drainage without fittings'),
    Gold is IS 4985:2021.
    If the engine recommends IS 18166:2025, even with full scope, lifecycle, and provenance,
    the evaluator MUST detect:
    wrong_primary_promotion_rate > 0
    safe_primary_rate == 0
    unsafe_primary_rate > 0
    """
    query = {
        "query_id": "Q_ADV_005",
        "raw_query": "Supply of uPVC pipes for agricultural drainage without fittings",
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_standards": [
            {
                "standard_designation": "IS 4985:2021",
                "base_number": "4985",
                "department": "CED",
            }
        ],
        "expected_decision": {
            "query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE"
        }
    }

    # Simulated output where engine promoted IS 18166:2025 with full evidence
    output = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "standard_designation": "IS 18166:2025",
            "base_number": "18166",
            "standard_role": "PRODUCT_SPECIFICATION",
            "evidence_bundle": {
                "identity_ready": True,
                "scope_ready": True,
                "applicability_ready": True,
                "lifecycle_ready": True,
                "provenance_ready": True,
                "standard_role": "PRODUCT_SPECIFICATION",
                "base_number": "18166",
            },
            "lifecycle": {
                "status": "ACTIVE",
                "is_superseded": False,
            },
            "scope": "This standard covers unplasticized polyvinyl chloride pipes...",
            "source_department": "CED",
        },
        "candidate_recommendations": [
            {"standard_designation": "IS 18166:2025"}
        ],
    }

    res = compute_safety_metrics([query], [output])

    assert res["wrong_primary_promotion_rate"] == 1.0, (
        f"Expected wrong_primary_promotion_rate == 1.0, got {res['wrong_primary_promotion_rate']}"
    )
    assert res["safe_primary_rate"] == 0.0, (
        f"Expected safe_primary_rate == 0.0, got {res['safe_primary_rate']}"
    )
    assert res["unsafe_primary_rate"] == 1.0, (
        f"Expected unsafe_primary_rate == 1.0, got {res['unsafe_primary_rate']}"
    )
    assert res["unsupported_primary_promotion_rate"] == 0.0, (
        "Evidence was present, so unsupported rate should be 0.0"
    )


def test_unsupported_primary_detected():
    """Verifies that a primary lacking evidence readiness is flagged as unsupported."""
    query = {
        "query_id": "Q_UNSUPPORTED",
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_standards": [{"standard_designation": "IS 4984:2016"}],
    }
    output = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "standard_designation": "IS 4984:2016",
            "standard_role": "PRODUCT_SPECIFICATION",
            "evidence_bundle": {
                "identity_ready": True,
                "scope_ready": False,  # Missing scope
                "applicability_ready": True,
                "lifecycle_ready": True,
                "provenance_ready": False,  # Missing provenance
            },
        },
    }

    assert is_primary_unsupported(output["primary_recommendation"]) is True

    res = compute_safety_metrics([query], [output])
    assert res["unsupported_primary_promotion_rate"] == 1.0
    assert res["safe_primary_rate"] == 0.0
    assert res["unsafe_primary_rate"] == 1.0


def test_wrong_role_primary_detected():
    """Verifies that promoting a test method or supporting standard as primary is flagged."""
    primary = {
        "standard_designation": "IS 2:1960",
        "standard_role": "TEST_METHOD",
        "evidence_bundle": {
            "standard_role": "TEST_METHOD",
        },
    }
    assert is_primary_wrong_role(primary) is True

    query = {
        "query_id": "Q_ROLE",
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_standards": [{"standard_designation": "IS 4984:2016"}],
    }
    output = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": primary,
    }
    res = compute_safety_metrics([query], [output])
    assert res["wrong_role_primary_rate"] == 1.0


def test_wrong_part_primary_detected():
    """Verifies that selecting the wrong part from the same base standard family is tracked."""
    query = {
        "query_id": "Q_PART",
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_standards": [
            {
                "standard_designation": "IS 2026 (Part 2):2010",
                "base_number": "2026",
            }
        ],
    }
    output = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "standard_designation": "IS 2026 (Part 1):2011",
            "base_number": "2026",
            "standard_role": "PRODUCT_SPECIFICATION",
            "evidence_bundle": {
                "identity_ready": True,
                "scope_ready": True,
                "applicability_ready": True,
                "lifecycle_ready": True,
                "provenance_ready": True,
                "base_number": "2026",
                "standard_role": "PRODUCT_SPECIFICATION",
            },
            "lifecycle": {"status": "ACTIVE", "is_superseded": False},
        },
    }
    res = compute_safety_metrics([query], [output])
    assert res["wrong_part_primary_rate"] == 1.0
    assert res["wrong_primary_promotion_rate"] == 1.0


def test_wrong_edition_primary_detected():
    """Verifies that promoting a superseded edition is flagged."""
    primary = {
        "standard_designation": "IS 7098 (Part 1):1988",
        "lifecycle": {
            "status": "SUPERSEDED",
            "is_superseded": True,
        },
    }
    assert is_primary_wrong_edition(primary) is True

    query = {
        "query_id": "Q_EDITION",
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_standards": [{"standard_designation": "IS 7098 (Part 1):2025"}],
    }
    output = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": primary,
    }
    res = compute_safety_metrics([query], [output])
    assert res["wrong_edition_primary_rate"] == 1.0


def test_regulatory_false_assertion_detected():
    """Verifies that misasserting regulatory status against authoritative gold is flagged."""
    query = {
        "query_id": "Q_REG",
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "expected_regulatory_status": "MANDATORY",
        "gold_standards": [{"standard_designation": "IS 694:2010"}],
    }
    output = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "standard_designation": "IS 694:2010",
            "regulatory": {
                "regulatory_state": "NOT_MANDATORY",
            },
            "evidence_bundle": {
                "identity_ready": True,
                "scope_ready": True,
                "applicability_ready": True,
                "lifecycle_ready": True,
                "provenance_ready": True,
                "standard_role": "PRODUCT_SPECIFICATION",
            },
            "lifecycle": {"status": "ACTIVE", "is_superseded": False},
        },
    }
    res = compute_safety_metrics([query], [output])
    assert res["regulatory_false_assertion_rate"] == 1.0


def test_safe_primary_recommendation_all_criteria_met():
    """Verifies that a fully compliant primary recommendation achieves 100% safe primary rate."""
    query = {
        "query_id": "Q_SAFE",
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_standards": [{"standard_designation": "IS 4984:2016", "base_number": "4984"}],
    }
    output = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "standard_designation": "IS 4984:2016",
            "base_number": "4984",
            "standard_role": "PRODUCT_SPECIFICATION",
            "evidence_bundle": {
                "identity_ready": True,
                "scope_ready": True,
                "applicability_ready": True,
                "lifecycle_ready": True,
                "provenance_ready": True,
                "base_number": "4984",
                "standard_role": "PRODUCT_SPECIFICATION",
            },
            "lifecycle": {"status": "ACTIVE", "is_superseded": False},
        },
    }
    res = compute_safety_metrics([query], [output])
    assert res["safe_primary_rate"] == 1.0
    assert res["wrong_primary_promotion_rate"] == 0.0
    assert res["unsupported_primary_promotion_rate"] == 0.0
    assert res["wrong_role_primary_rate"] == 0.0
    assert res["wrong_edition_primary_rate"] == 0.0
    assert res["unsafe_primary_rate"] == 0.0


def test_safe_abstention_no_opportunities():
    """Section 45: Denominator is zero when no queries require abstention -> rate is None, bounded."""
    query = {
        "query_id": "Q_IN_SCOPE_1",
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_standards": [{"standard_designation": "IS 4984:2016", "base_number": "4984"}],
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE"},
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "expected_evidence_state": "SCOPE_AVAILABLE",
    }
    output = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "standard_designation": "IS 4984:2016",
            "base_number": "4984",
            "standard_role": "PRODUCT_SPECIFICATION",
            "evidence_bundle": {
                "scope_ready": True, "applicability_ready": True,
                "lifecycle_ready": True, "provenance_ready": True,
            },
            "lifecycle": {"status": "ACTIVE", "is_superseded": False},
        },
    }
    res = compute_safety_metrics([query], [output])
    assert res["abstention_opportunities"] == 0
    assert res["safe_abstentions_count"] == 0
    assert res["safe_abstention_rate"] is None


def test_safe_abstention_one_opportunity_safe():
    """Section 45: One query expecting abstention, engine safely abstains -> rate 1.0."""
    query = {
        "query_id": "Q_ABSTAIN_1",
        "expected_coverage_state": "OUTSIDE_PROTOTYPE_COVERAGE",
        "gold_standards": [],
        "expected_decision": {"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE"},
    }
    output = {
        "decision_state": "OUTSIDE_PROTOTYPE_COVERAGE",
        "primary_recommendation": None,
        "review_candidate": None,
    }
    res = compute_safety_metrics([query], [output])
    assert res["abstention_opportunities"] == 1
    assert res["safe_abstentions_count"] == 1
    assert res["safe_abstention_rate"] == 1.0


def test_safe_abstention_one_opportunity_false():
    """Section 45: One query expecting abstention, engine wrongly emits primary -> rate 0.0."""
    query = {
        "query_id": "Q_ABSTAIN_2",
        "expected_coverage_state": "OUTSIDE_PROTOTYPE_COVERAGE",
        "gold_standards": [],
        "expected_decision": {"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE"},
    }
    output = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "standard_designation": "IS 9999:2020",
            "standard_role": "PRODUCT_SPECIFICATION",
            "lifecycle": {"status": "ACTIVE", "is_superseded": False},
        },
        "review_candidate": None,
    }
    res = compute_safety_metrics([query], [output])
    assert res["abstention_opportunities"] == 1
    assert res["safe_abstentions_count"] == 0
    assert res["safe_abstention_rate"] == 0.0


def test_safe_abstention_mixed_population():
    """Section 45: Mixed set of abstention opportunities and primary recommendations."""
    queries = [
        # Opportunity 1: Outside coverage -> safely abstained
        {
            "query_id": "Q_1",
            "expected_coverage_state": "OUTSIDE_PROTOTYPE_COVERAGE",
            "gold_standards": [],
            "expected_decision": {"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE"},
        },
        # Opportunity 2: Insufficient info -> wrongly promoted primary
        {
            "query_id": "Q_2",
            "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
            "gold_standards": [],
            "expected_decision": {"query_level_state": "INSUFFICIENT_INFORMATION"},
        },
        # Opportunity 3: Expert review required -> safely abstained with review
        {
            "query_id": "Q_3",
            "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
            "gold_standards": [{"standard_designation": "IS 4984:2016"}],
            "expected_decision": {"query_level_state": "EXPERT_REVIEW_REQUIRED"},
        },
        # Non-opportunity: Clear primary expected
        {
            "query_id": "Q_4",
            "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
            "gold_standards": [{"standard_designation": "IS 4985:2021", "base_number": "4985"}],
            "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE"},
        },
    ]
    outputs = [
        {"decision_state": "OUTSIDE_PROTOTYPE_COVERAGE", "primary_recommendation": None},
        {"decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "primary_recommendation": {"standard_designation": "IS 1234:2020", "lifecycle": {"status": "ACTIVE"}}},
        {"decision_state": "EXPERT_REVIEW_REQUIRED", "primary_recommendation": None, "review_candidate": {"standard_designation": "IS 4984:2016"}},
        {"decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "primary_recommendation": {"standard_designation": "IS 4985:2021", "base_number": "4985", "standard_role": "PRODUCT_SPECIFICATION", "evidence_bundle": {"scope_ready": True, "applicability_ready": True, "lifecycle_ready": True, "provenance_ready": True}, "lifecycle": {"status": "ACTIVE"}}},
    ]

    res = compute_safety_metrics(queries, outputs)
    assert res["abstention_opportunities"] == 3
    assert res["safe_abstentions_count"] == 2
    assert res["safe_abstention_rate"] == round(2 / 3, 4)
    assert 0.0 <= res["safe_abstention_rate"] <= 1.0


def test_safe_abstention_all_primary_case():
    """Section 45: All queries are primary-eligible and system promotes all -> safe_abstention_rate is None."""
    queries = [
        {
            "query_id": f"Q_{i}",
            "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
            "gold_standards": [{"standard_designation": f"IS {i}:2020", "base_number": str(i)}],
            "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE"},
        }
        for i in range(1, 4)
    ]
    outputs = [
        {
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "primary_recommendation": {
                "standard_designation": f"IS {i}:2020",
                "base_number": str(i),
                "standard_role": "PRODUCT_SPECIFICATION",
                "evidence_bundle": {"scope_ready": True, "applicability_ready": True, "lifecycle_ready": True, "provenance_ready": True},
                "lifecycle": {"status": "ACTIVE"},
            }
        }
        for i in range(1, 4)
    ]
    res = compute_safety_metrics(queries, outputs)
    assert res["abstention_opportunities"] == 0
    assert res["safe_abstention_rate"] is None
    assert res["safe_primary_rate"] == 1.0


def test_safe_abstention_all_abstention_case():
    """Section 45: All queries require abstention and system safely abstains on all -> rate 1.0."""
    queries = [
        {
            "query_id": f"Q_ABS_{i}",
            "expected_coverage_state": "OUTSIDE_PROTOTYPE_COVERAGE",
            "gold_standards": [],
            "expected_decision": {"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE"},
        }
        for i in range(1, 4)
    ]
    outputs = [
        {"decision_state": "OUTSIDE_PROTOTYPE_COVERAGE", "primary_recommendation": None}
        for _ in range(3)
    ]
    res = compute_safety_metrics(queries, outputs)
    assert res["abstention_opportunities"] == 3
    assert res["safe_abstentions_count"] == 3
    assert res["safe_abstention_rate"] == 1.0
    assert res["safe_primary_rate"] is None  # Section 46: 0 primaries emitted -> None, not 1.0


def test_unverified_edition_flagged_as_wrong_edition():
    """Section 47: Promoting a candidate with UNKNOWN / UNVERIFIED lifecycle is flagged."""
    primary = {
        "standard_designation": "IS 1234:2020",
        "lifecycle": {
            "lifecycle_state": "LIFECYCLE_UNKNOWN",
            "status": "UNKNOWN",
            "is_superseded": None,
        }
    }
    assert is_primary_wrong_edition(primary) is True

    query = {
        "query_id": "Q_UNVERIFIED_EDITION",
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_standards": [{"standard_designation": "IS 1234:2020"}],
    }
    output = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": primary,
    }
    res = compute_safety_metrics([query], [output])
    assert res["wrong_edition_primary_rate"] == 1.0
    assert res["safe_primary_rate"] == 0.0

