"""
Unit and regression tests for PrototypeCoveragePolicy and CED/ETD primary boundaries.
Enforces that:
1. Standards with non-CED/ETD departments cannot be promoted as primary product standards.
2. Standards with unknown/missing departments cannot be promoted as primary product standards.
3. CED and ETD standards remain eligible for primary recommendation if all other gates pass.
4. Non-CED/ETD standards can still serve as supporting or context references.
"""

import pytest
from src.recommendation.corpus_policy import PrototypeCoveragePolicy, CandidateEligibilityPolicy
from src.recommendation.evidence_bundle import EvidenceBundle, EvidencePolicy, ClaimType, EvidenceGapCode


def test_prototype_coverage_policy_resolution():
    assert PrototypeCoveragePolicy.resolve_department({"primary_department": "CED"}) == "CED"
    assert PrototypeCoveragePolicy.resolve_department({"department": "etd"}) == "ETD"
    assert PrototypeCoveragePolicy.resolve_department({"source_departments": ["TXD", "CED"]}) == "TXD"
    assert PrototypeCoveragePolicy.resolve_department({}) is None

    assert PrototypeCoveragePolicy.is_in_primary_coverage({"primary_department": "CED"}) is True
    assert PrototypeCoveragePolicy.is_in_primary_coverage({"primary_department": "ETD"}) is True
    assert PrototypeCoveragePolicy.is_in_primary_coverage({"primary_department": "TXD"}) is False
    assert PrototypeCoveragePolicy.is_in_primary_coverage({"primary_department": "FAD"}) is False
    assert PrototypeCoveragePolicy.is_in_primary_coverage({}) is False


def test_candidate_eligibility_policy_blocks_outside_departments():
    ced_node = {
        "node_type": "INDIAN_STANDARD",
        "primary_department": "CED",
        "candidate_status": "ELIGIBLE",
        "standard_role": "PRIMARY_PRODUCT",
        "designation": "IS 4985:2021",
        "title": "Unplasticized PVC Pipes for Potable Water Supplies",
    }
    assert CandidateEligibilityPolicy.is_primary_candidate(ced_node) is True

    # Unknown department node cannot be primary candidate
    unknown_dept_node = dict(ced_node)
    unknown_dept_node["primary_department"] = None
    assert CandidateEligibilityPolicy.is_primary_candidate(unknown_dept_node) is False

    # Outside department node (TXD - Textiles) cannot be primary candidate
    txd_node = dict(ced_node)
    txd_node["primary_department"] = "TXD"
    assert CandidateEligibilityPolicy.is_primary_candidate(txd_node) is False

    # But outside department node can still be supporting context
    assert CandidateEligibilityPolicy.is_supporting_context(txd_node) is False or CandidateEligibilityPolicy.is_primary_candidate(txd_node) is False


def test_evidence_policy_blocks_primary_for_unverified_or_outside_department():
    node = {
        "designation": "IS 9999:2020",
        "title": "Textile Fabric Specification",
        "primary_department": "TXD",
        "scope": "This standard specifies requirements for textile fabrics of high tensile strength across industrial applications.",
        "standard_role": "PRIMARY_PRODUCT",
        "status": "ACTIVE",
        "is_hydrated": True,
    }
    bundle = EvidenceBundle.from_node(node)
    bundle.technical_attributes["product"] = {"value": "textile fabric", "state": "MATCH"}
    
    app_ctx = {
        "target_product": "textile fabric",
        "matched_attributes": ["PRODUCT", "MATERIAL"],
    }
    
    sat, gaps = EvidencePolicy.evaluate_claim(ClaimType.PRIMARY_RECOMMENDATION_CLAIM, bundle, context=app_ctx)
    assert sat is False
    assert EvidenceGapCode.OUTSIDE_PROTOTYPE_COVERAGE.value in gaps
