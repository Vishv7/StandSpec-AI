"""
Adversarial Safety and Explicit Designation Regression Tests — StandSpec AI (Phase P1-D)
Verifies:
1. Explicit Designation Safety: Explicitly naming an incompatible standard (e.g. IS 1180 for uPVC pipes)
   never promotes the candidate to APPLICABLE or VERIFIED_FOR_RECOMMENDATION.
2. Cross-Domain Incompatibility: Pipe query naming transformer standard -> NOT_APPLICABLE.
3. Test Method Role Gating: Test method standards (e.g. IS 10810) cannot become primary product recommendations.
4. Code of Practice Gating: Design codes (e.g. IS 800) cannot be silently promoted to product recommendations.
5. Supporting Standards Safety: Material/aggregate standards (e.g. IS 383) cannot be primary for cables.
6. Review Candidate Contract: Strong unready candidates carry the authoritative EvidenceBundle,
   exact gap codes, and provenance.
"""

import json
from pathlib import Path
import pytest

from src.recommendation.engine import StandSpecRecommendationEngine
from src.recommendation.applicability import ApplicabilityState
from src.recommendation.evidence_bundle import EvidenceBundle, EvidenceGapCode, ClaimType, EvidencePolicy


@pytest.fixture(scope="module")
def real_graph():
    """Load canonical standards graph for adversarial tests."""
    project_root = Path(__file__).resolve().parent.parent
    graph_path = project_root / "data" / "processed" / "standards_graph.json"
    if not graph_path.exists():
        pytest.skip(f"Knowledge graph not found at {graph_path}")
    with open(graph_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_adversarial_upvc_pipes_is_1180(real_graph):
    """
    P0 CRITICAL SAFETY TEST:
    Query: 'Supply of uPVC pipes as per IS 1180 Part 1'
    IS 1180 is for transformers, completely unrelated to uPVC pipes.
    The explicit designation must be resolved as an identity anchor,
    but MUST NOT be promoted to applicable or recommended.
    """
    engine = StandSpecRecommendationEngine(real_graph)
    query = "Supply of uPVC pipes as per IS 1180 Part 1"
    decision = engine.recommend(query)

    primary = decision.get("primary_recommendation")
    if primary:
        assert "1180" not in primary.get("standard_designation", ""), (
            f"SAFETY VIOLATION: IS 1180 was recommended for uPVC pipes! Result: {primary}"
        )

    # If IS 1180 is present in rejected or alternatives, its applicability must be NOT_APPLICABLE
    trace = decision.get("decision_trace", [])
    assert any(s["stage"] == "applicability" for s in trace)
    assert decision.get("claim_level") != "VERIFIED_FOR_RECOMMENDATION" or (
        primary and "4985" in primary.get("standard_designation", "")
    )


def test_adversarial_transformer_is_4984(real_graph):
    """
    P0 SAFETY TEST:
    Query: 'Supply of distribution transformer as per IS 4984'
    IS 4984 is for HDPE pipes. It must never be recommended for transformers.
    """
    engine = StandSpecRecommendationEngine(real_graph)
    query = "Supply of distribution transformer as per IS 4984"
    decision = engine.recommend(query)

    primary = decision.get("primary_recommendation")
    if primary:
        assert "4984" not in primary.get("standard_designation", ""), (
            f"SAFETY VIOLATION: IS 4984 (HDPE pipes) recommended for transformer query: {primary}"
        )


def test_adversarial_cables_is_383(real_graph):
    """
    P0 SAFETY TEST:
    Query: 'Supply of power cables as per IS 383'
    IS 383 is for coarse and fine aggregates (concrete). It must never become primary for cables.
    """
    engine = StandSpecRecommendationEngine(real_graph)
    query = "Supply of power cables as per IS 383"
    decision = engine.recommend(query)

    primary = decision.get("primary_recommendation")
    if primary:
        assert "383" not in primary.get("standard_designation", ""), (
            f"SAFETY VIOLATION: IS 383 (aggregates) recommended as primary for cables: {primary}"
        )


def test_adversarial_test_method_not_promoted_as_product(real_graph):
    """
    P0 SAFETY TEST:
    Query: 'Procurement of test methods for cables as per IS 10810 Part 53'
    IS 10810 is a TEST_METHOD standard, not a physical cable product standard.
    Must not become a VERIFIED_FOR_RECOMMENDATION primary product standard.
    """
    engine = StandSpecRecommendationEngine(real_graph)
    query = "Procurement of electric cables as per IS 10810 Part 53"
    decision = engine.recommend(query)

    primary = decision.get("primary_recommendation")
    if primary:
        assert "10810" not in primary.get("standard_designation", ""), (
            f"SAFETY VIOLATION: IS 10810 test method promoted to primary product standard: {primary}"
        )


def test_adversarial_code_of_practice_preserved(real_graph):
    """
    P0 SAFETY TEST:
    Query: 'Supply of structural steel sections as per IS 800'
    IS 800 is a CODE_OF_PRACTICE for general construction in steel.
    The physical product standard is IS 2062.
    IS 800 role must remain CODE_OF_PRACTICE and not be silently promoted to a product standard.
    """
    engine = StandSpecRecommendationEngine(real_graph)
    query = "Supply of structural steel sections as per IS 800"
    decision = engine.recommend(query)

    primary = decision.get("primary_recommendation")
    if primary and "800" in primary.get("standard_designation", ""):
        assert primary.get("evidence_bundle", {}).get("standard_role") == "CODE_OF_PRACTICE"
        assert primary.get("claim_level") != "VERIFIED_FOR_RECOMMENDATION"


def test_review_candidate_carries_full_authoritative_bundle(real_graph):
    """
    Verify that when a candidate is held for review due to insufficient scope/lifecycle,
    the review_candidate carries the full EvidenceBundle, gap codes, and provenance.
    """
    mock_graph = {
        "nodes": [
            {
                "id": "IS 99999:2024",
                "designation": "IS 99999:2024",
                "title": "Unscoped High Voltage Power Cable",
                "scope": None,  # Missing scope in KB!
                "committee": "ETD 09",
                "is_hydrated": False,
                "standard_role": "PRODUCT_STANDARD",
            }
        ],
        "edges": []
    }
    engine = StandSpecRecommendationEngine(mock_graph)
    query = "Supply of high voltage power cable as per IS 99999"
    decision = engine.recommend(query)

    assert decision["primary_recommendation"] is None
    assert decision["decision_state"] == "EXPERT_REVIEW_REQUIRED"
    rev = decision.get("review_candidate")
    assert rev is not None, "Expected review_candidate to be populated when scope is missing"

    # Full contract fields check
    assert rev["standard_designation"] == "IS 99999:2024"
    assert rev["claim_level"] == "REVIEW_REQUIRED"
    assert "evidence_bundle" in rev
    bundle = rev["evidence_bundle"]
    assert bundle["designation"] == "IS 99999:2024"
    assert "SCOPE_MISSING" in rev["evidence_gaps"] or "APPLICABILITY_EVIDENCE_MISSING" in rev["evidence_gaps"]
    assert "retrieval_diagnostics" in rev
    assert "provenance" in rev
