"""
Unit Tests for EvidencePolicy, ClaimType, and EvidenceGapCode — StandSpec AI (P1-C)
Verifies:
1. Separation of TECHNICAL_APPLICABILITY_CLAIM from REGULATORY_MANDATE_CLAIM.
2. Evidence gap codes emitted accurately for incomplete bundles.
3. Decision trace produces explicit 'state' for all 14 stages.
4. Monotonic claim levels cannot promote candidates without passing all upstream gates.
5. Review candidate surfaces complete evidence gaps.
"""

import pytest
from src.recommendation.evidence_bundle import (
    EvidenceBundle,
    EvidenceItem,
    EvidencePolicy,
    ClaimType,
    EvidenceGapCode,
)
from src.recommendation.engine import StandSpecRecommendationEngine


def test_claim_separation_technical_vs_regulatory():
    """
    A standard can satisfy TECHNICAL_APPLICABILITY_CLAIM without satisfying
    REGULATORY_MANDATE_CLAIM, and vice versa.
    """
    bundle = EvidenceBundle(
        designation="IS 1234:2020",
        title="Specification for Test Product",
        department="CED",
        base_number=1234,
        year="2020",
    )
    bundle.raw_scope = "This standard specifies requirements for manufacturing test products."
    bundle.lifecycle_evidence["status"] = "ACTIVE"
    bundle.provenance_metadata["is_hydrated"] = True

    # Regulatory status is unverified
    bundle.regulatory_evidence["regulatory_state"] = "NOT_VERIFIED_IN_CURRENT_CORPUS"

    tech_sat, tech_gaps = EvidencePolicy.evaluate_claim(ClaimType.TECHNICAL_APPLICABILITY_CLAIM, bundle)
    assert tech_sat is True
    assert not tech_gaps

    reg_sat, reg_gaps = EvidencePolicy.evaluate_claim(ClaimType.REGULATORY_MANDATE_CLAIM, bundle)
    assert reg_sat is False
    assert EvidenceGapCode.REGULATORY_UNVERIFIED.value in reg_gaps


def test_scope_missing_gap_code():
    """Missing scope emits SCOPE_MISSING gap code on primary recommendation claim."""
    bundle = EvidenceBundle(
        designation="IS 9999:2021",
        title="Unscoped Product Standard",
        department="CED",
        base_number=9999,
        year="2021",
    )
    bundle.raw_scope = None
    bundle.lifecycle_evidence["status"] = "ACTIVE"

    sat, gaps = EvidencePolicy.evaluate_claim(ClaimType.PRIMARY_RECOMMENDATION_CLAIM, bundle)
    assert sat is False
    assert EvidenceGapCode.SCOPE_MISSING.value in gaps


def test_lifecycle_unverified_gap_code():
    """Unknown or unverified lifecycle status emits LIFECYCLE_UNVERIFIED gap code."""
    bundle = EvidenceBundle(
        designation="IS 8888:2019",
        title="Product with Unknown Lifecycle",
        department="ETD",
        base_number=8888,
        year="2019",
    )
    bundle.raw_scope = "Substantive scope text for product verification testing."
    bundle.lifecycle_evidence["status"] = "UNKNOWN"

    sat, gaps = EvidencePolicy.evaluate_claim(ClaimType.PRIMARY_RECOMMENDATION_CLAIM, bundle)
    assert sat is False
    assert EvidenceGapCode.LIFECYCLE_UNVERIFIED.value in gaps


def test_role_mismatch_gap_code():
    """Auxiliary or test method roles cannot be primary recommendations."""
    bundle = EvidenceBundle(
        designation="IS 10810 (Part 1):1984",
        title="Methods of test for cables",
        department="ETD",
        base_number=10810,
        part="1",
        year="1984",
        standard_role="TEST_METHOD",
    )
    bundle.raw_scope = "This standard covers methods of testing electric cables."
    bundle.lifecycle_evidence["status"] = "ACTIVE"
    bundle.provenance_metadata["is_hydrated"] = True

    sat, gaps = EvidencePolicy.evaluate_claim(ClaimType.PRIMARY_RECOMMENDATION_CLAIM, bundle)
    assert sat is False
    assert EvidenceGapCode.ROLE_MISMATCH.value in gaps


def test_decision_trace_explicit_state_contract():
    """Verify that all 14 stages in DecisionTrace output explicit 'state' and 'status'."""
    engine = StandSpecRecommendationEngine({"nodes": [], "edges": []})
    res = engine.recommend("Procure standard conforming to IS 4984 for water pipes")
    trace = res.get("decision_trace", [])
    assert len(trace) == 14

    allowed_states = {"PASS", "FAIL", "BLOCKED", "UNKNOWN", "SKIPPED", "CONFLICT"}
    for step in trace:
        assert "state" in step
        assert "status" in step
        assert step["state"] == step["status"]
        assert step["state"] in allowed_states
        assert "stage" in step
        assert "reason" in step
        assert "evidence" in step
        assert "blocking" in step


def test_unknown_role_gap_code():
    """Mentor review Part 2: UNKNOWN_ROLE must emit ROLE_UNVERIFIED gap code and cannot be primary."""
    bundle = EvidenceBundle(
        designation="IS 99999:2020",
        title="Unclassified Testing Procedure or Standard",
        department="CED",
        base_number=99999,
        year="2020",
        standard_role="UNKNOWN_ROLE",
    )
    bundle.raw_scope = "Scope covering arbitrary unclassified operations without product indicators."
    bundle.lifecycle_evidence["status"] = "ACTIVE"
    bundle.provenance_metadata["is_hydrated"] = True

    sat, gaps = EvidencePolicy.evaluate_claim(ClaimType.PRIMARY_RECOMMENDATION_CLAIM, bundle)
    assert sat is False
    assert EvidenceGapCode.ROLE_UNVERIFIED.value in gaps


def test_unknown_role_ineligible_for_physical_procurement():
    """Mentor review Part 2: UNKNOWN_ROLE cannot be primary candidate when intent is physical procurement."""
    from src.recommendation.corpus_policy import CandidateEligibilityPolicy
    node = {
        "designation": "IS 99999:2020",
        "title": "Unclassified Operations",
        "standard_role": "UNKNOWN_ROLE",
    }
    assert CandidateEligibilityPolicy.is_primary_candidate(node, intent="SUPPLY") is False
    assert CandidateEligibilityPolicy.is_supporting_context(node) is True

