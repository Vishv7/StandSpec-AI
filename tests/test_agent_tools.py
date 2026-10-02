"""
Tests for StandSpec AI Agent Tools (Phase P1-F Section 6)
Verifies the 7 official BIS tools:
1. search_standards
2. get_standard_evidence
3. check_applicability
4. check_lifecycle
5. check_regulatory
6. check_prototype_coverage
7. get_standard_relationships
"""

import pytest
from src.agent.tool_registry import ToolRegistry, Tool
from src.agent.tool_router import ToolRouter
from src.recommendation.engine import StandSpecRecommendationEngine


@pytest.fixture(scope="module")
def tool_router():
    """Initializes ToolRouter using engine initialized from release artifacts."""
    engine = StandSpecRecommendationEngine.from_release()
    return ToolRouter(engine=engine)


@pytest.fixture(scope="module")
def registry(tool_router):
    return tool_router.build_registry()


def test_registry_registration_and_dispatch(registry):
    """Verify that all 7 official tools are registered with schemas."""
    expected_tools = {
        "search_standards",
        "get_standard_evidence",
        "check_applicability",
        "check_lifecycle",
        "check_regulatory",
        "check_prototype_coverage",
        "get_standard_relationships",
    }
    registered = set(registry.list_names())
    assert expected_tools.issubset(registered)

    # Calling an unknown tool returns an error status
    unknown_res = registry.dispatch("nonexistent_tool", {})
    assert unknown_res["status"] == "ERROR"
    assert "Unknown tool" in unknown_res["error_message"]


def test_tool_search_standards(registry):
    """Verify search_standards tool returns ranked candidate standards."""
    res = registry.dispatch("search_standards", {
        "query": "11 kV XLPE insulated three-core power cable",
        "top_k": 5,
    })
    assert res["status"] == "SUCCESS"
    assert "candidates" in res
    assert len(res["candidates"]) > 0

    top_cand = res["candidates"][0]
    assert "designation" in top_cand
    assert "title" in top_cand
    assert "role" in top_cand
    assert "department" in top_cand
    assert "retrieval_score" in top_cand


def test_tool_get_standard_evidence(registry):
    """Verify get_standard_evidence returns structured EvidenceBundle."""
    # Test with standard present in CED/ETD
    res = registry.dispatch("get_standard_evidence", {"designation": "IS 4984:2016"})
    assert res["status"] == "SUCCESS"
    assert "evidence" in res
    ev = res["evidence"]
    assert "designation" in ev
    assert "title" in ev
    assert "scope" in ev


def test_tool_check_applicability(registry):
    """Verify check_applicability evaluates per-attribute match/mismatch."""
    # IS 7098 (Part 2) is applicable for 11 kV XLPE cable
    res = registry.dispatch("check_applicability", {
        "designation": "IS 7098 (Part 2):2011",
        "query": "Supply of 11 kV XLPE insulated power cables",
    })
    assert res["status"] == "SUCCESS"
    assert res["applicability_state"] in ("APPLICABLE", "CONDITIONALLY_APPLICABLE", "MATCH", "EXPERT_REVIEW_REQUIRED")
    assert "matched_attributes" in res


def test_tool_check_lifecycle(registry):
    """Verify check_lifecycle evaluates active/superseded status as of contemporary date."""
    res = registry.dispatch("check_lifecycle", {
        "designation": "IS 4984:2016",
        "evaluation_date": "2026-07-15",
    })
    assert res["status"] == "SUCCESS"
    assert res["lifecycle_state"] in (
        "ACTIVE_VALID", "ACTIVE", "SUPERSEDED",
        "VERIFIED_ACTIVE", "VERIFIED_SUPERSEDED", "LIFECYCLE_UNVERIFIED",
    )


def test_tool_check_regulatory_never_claims_voluntary_on_unverified(registry):
    """Verify check_regulatory never claims not mandatory when unverified."""
    res = registry.dispatch("check_regulatory", {
        "designation": "IS 4984:2016",
    })
    assert res["status"] == "SUCCESS"
    assert "regulatory_state" in res
    assert "statement" in res
    if res["regulatory_state"] in ("NOT_VERIFIED_IN_CURRENT_CORPUS", "UNVERIFIED"):
        assert "not mandatory" not in res["statement"].lower()
        assert "voluntary" not in res["statement"].lower()
        assert "not verified" in res["statement"].lower()


def test_tool_check_prototype_coverage(registry):
    """Verify check_prototype_coverage correctly isolates CED and ETD."""
    ced_res = registry.dispatch("check_prototype_coverage", {"department": "CED"})
    assert ced_res["coverage_state"] == "IN_PROTOTYPE_COVERAGE"

    etd_res = registry.dispatch("check_prototype_coverage", {"department": "ETD"})
    assert etd_res["coverage_state"] == "IN_PROTOTYPE_COVERAGE"

    med_res = registry.dispatch("check_prototype_coverage", {"department": "MED"})
    assert med_res["coverage_state"] == "OUTSIDE_PROTOTYPE_COVERAGE"


def test_tool_get_standard_relationships(registry):
    """Verify get_standard_relationships extracts parts, test methods, and superseding edges."""
    res = registry.dispatch("get_standard_relationships", {"designation": "IS 7098 (Part 2)"})
    assert res["status"] == "SUCCESS"
    assert "relationships" in res
    rels = res["relationships"]
    assert "parts" in rels
    assert "test_methods" in rels
    assert "supporting_standards" in rels
