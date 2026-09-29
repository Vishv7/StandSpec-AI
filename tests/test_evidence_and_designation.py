"""
Tests for Evidence Gate Enforcement (P0-2) and Exact Designation Intent (P0-6).
Verifies that:
1. Candidates without verified scope evidence (e.g. IS 2553 for 6 mm safety glass) cannot become
   confident primary recommendations and degrade safely to EXPERT_REVIEW_REQUIRED.
2. Explicit designation queries (e.g. IS 7098 Part 2, IS 4984:2016, IS 302 Part 2/Sec 16)
   are deterministically resolved and prioritized over generic semantic retrieval.
3. Any recommendation for a candidate with recommendation_ready=False includes an explicit evidence exception.
"""

import json
from pathlib import Path
import pytest

from src.recommendation.engine import StandSpecRecommendationEngine
from src.retrieval.designation_resolver import DesignationResolver


GRAPH_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "standards_graph.json"


@pytest.fixture(scope="module")
def full_engine():
    if not GRAPH_PATH.exists():
        pytest.skip(f"Knowledge graph not found at {GRAPH_PATH}")
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    return StandSpecRecommendationEngine(graph)


def test_safety_glass_evidence_gating(full_engine):
    """
    P0-2 Regression Test:
    'procurement of 6 mm safety glass for building glazing' must NOT produce
    PRIMARY_RECOMMENDATION_AVAILABLE from an unhydrated stub without verified scope evidence.
    Must degrade to EXPERT_REVIEW_REQUIRED with primary_recommendation=None.
    """
    res = full_engine.recommend("procurement of 6 mm safety glass for building glazing")
    assert res["decision_state"] == "EXPERT_REVIEW_REQUIRED"
    assert res["primary_recommendation"] is None
    assert "lacks verified scope evidence" in res["abstention_reason"]
    assert ("IS 2553" in res["abstention_reason"] or "IS 16978" in res["abstention_reason"])


def test_exact_designation_xlpe_cable(full_engine):
    """
    P0-1, P0-3 & P0-6 Regression Test:
    'Supply standard complying with IS 7098 Part 2 for 11 kV XLPE cable.'
    must resolve IS 7098 (Part 2):2011 as the top candidate,
    preventing generic retrieval from displacing it with IS 13573 (Part 2).
    """
    res = full_engine.recommend("Supply standard complying with IS 7098 Part 2 for 11 kV XLPE cable.")
    assert res["decision_state"] in ("INSUFFICIENT_INFORMATION", "EXPERT_REVIEW_REQUIRED", "PRIMARY_RECOMMENDATION_AVAILABLE")
    cand = res.get("primary_recommendation") or res.get("review_candidate")
    assert cand is not None
    desig = cand.get("standard_designation") or cand.get("designation")
    assert "IS 7098 (Part 2)" in desig


def test_exact_designation_hdpe_pipe(full_engine):
    """
    P0-1, P0-3 & P0-6 Regression Test:
    Explicit designation IS 4984:2016 for water supply must be resolved deterministically.
    """
    res = full_engine.recommend("Please procure IS 4984:2016 HDPE pipes for water supply.")
    assert res["decision_state"] in ("EXPERT_REVIEW_REQUIRED", "INSUFFICIENT_INFORMATION", "PRIMARY_RECOMMENDATION_AVAILABLE")
    cand = res.get("primary_recommendation") or res.get("review_candidate")
    assert cand is not None
    desig = cand.get("standard_designation") or cand.get("designation")
    assert "IS 4984" in desig


def test_exact_designation_food_waste_disposer(full_engine):
    """
    P0-1, P0-3 & P0-6 Regression Test:
    Explicit designation IS 302 Part 2/Sec 16 for kitchen waste disposer must resolve correctly.
    """
    res = full_engine.recommend("Please procure IS 302 Part 2/Sec 16 for kitchen waste disposer.")
    assert res["decision_state"] in ("EXPERT_REVIEW_REQUIRED", "CONDITIONAL_RECOMMENDATION", "PRIMARY_RECOMMENDATION_AVAILABLE")
    cand = res.get("primary_recommendation") or res.get("review_candidate")
    assert cand is not None
    desig = cand.get("standard_designation") or cand.get("designation")
    assert "IS 302 (Part 2/Sec 16)" in desig


def test_evidence_exception_contract_compliance(full_engine):
    """
    P0-2 Contract Verification:
    No final primary recommendation may reference recommendation_ready=False
    unless an explicit evidence exception is documented and represented in the result.
    """
    res = full_engine.recommend("High density polyethylene pipes for rural potable water distribution network PE 100 PN 10")
    if res["primary_recommendation"]:
        rec = res["primary_recommendation"]
        if not rec.get("recommendation_ready", False):
            assert rec.get("evidence_exception") is not None
            assert len(rec["evidence_exception"]) > 0
