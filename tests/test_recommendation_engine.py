"""
Tests for Recommendation Subsystem (Phases 13, 14, 15, 16).
Verifies technical applicability gating, lifecycle chain resolution,
regulatory status evaluation, and end-to-end recommendation workflow.
"""

import pytest
from src.recommendation import (
    TechnicalApplicabilityEngine,
    ApplicabilityState,
    LifecycleGate,
    RegulatoryGate,
    RegulatoryState,
    StandSpecRecommendationEngine,
)


@pytest.fixture
def mini_graph():
    return {
        "nodes": [
            {
                "id": "IS 7098 (Part 2):2011",
                "designation": "IS 7098 (Part 2):2011",
                "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables For Working Voltages From 3.3 kV Up To 33 kV",
                "scope": "Covers XLPE insulated cables for 11 kV to 33 kV applications.",
                "committee": "ETD 09",
                "is_hydrated": True,
                "is_recommendation_eligible": True,
                "recommendation_ready": True,
                "publication_date": "2011-01-01",
                "lifecycle_status": "ACTIVE",
            },
            {
                "id": "IS 1554 (Part 1):1988",
                "designation": "IS 1554 (Part 1):1988",
                "title": "PVC Insulated Electric Cables for Working Voltages up to 1100V",
                "scope": "Covers PVC insulated cables up to 1100 V.",
                "committee": "ETD 09",
                "is_hydrated": True,
                "is_recommendation_eligible": True,
                "recommendation_ready": True,
            },
            {
                "id": "IS 10810 (Part 53):1984",
                "designation": "IS 10810 (Part 53):1984",
                "title": "Methods of Test for Cables: Part 53 Flammability Test",
                "scope": "Method of test for flammability.",
                "committee": "ETD 09",
                "is_hydrated": True,
                "is_recommendation_eligible": False,
                "recommendation_ready": False,
            },
            {
                "id": "IS 1180 (Part 1):2014",
                "designation": "IS 1180 (Part 1):2014",
                "title": "Outdoor Type Oil Immersed Distribution Transformers Up to and Including 2500 kVA",
                "scope": "Covers distribution transformers up to 2500 kVA.",
                "committee": "ETD 16",
                "is_hydrated": True,
                "is_recommendation_eligible": True,
                "recommendation_ready": True,
            },
            {
                "id": "IS 2026 (Part 1):2011",
                "designation": "IS 2026 (Part 1):2011",
                "title": "Power transformers: Part 1 general",
                "scope": "General requirements for power transformers.",
                "committee": "ETD 16",
                "is_hydrated": True,
                "is_recommendation_eligible": True,
                "recommendation_ready": True,
            },
        ],
        "edges": [
            {
                "source": "IS 7098 (Part 2):2011",
                "target": "IS 10810 (Part 53):1984",
                "relationship": "test_method",
                "relationship_confidence_state": "HIGH",
            }
        ],
    }


def test_applicability_scope_exclusion_transformer():
    """Verify IS 1180 is excluded for 500 MVA power transformer requirements."""
    engine = TechnicalApplicabilityEngine()
    candidate = {"designation": "IS 1180 (Part 1):2014", "title": "Distribution Transformers"}
    requirement = {"raw_text": "500 MVA 400 kV autotransformer for grid substation"}

    eval_res = engine.evaluate_applicability(candidate, requirement)
    assert eval_res["state"] == ApplicabilityState.NOT_APPLICABLE.value
    assert not eval_res["is_applicable"]
    assert "strictly limited to distribution transformers" in eval_res["rejection_reason"]


def test_applicability_voltage_exclusion_cable():
    """Verify IS 1554 is excluded for 11 kV cable requirements."""
    engine = TechnicalApplicabilityEngine()
    candidate = {"designation": "IS 1554 (Part 1):1988", "title": "PVC Insulated Electric Cables up to 1100V"}
    requirement = {"raw_text": "11 kV XLPE insulated underground cable"}

    eval_res = engine.evaluate_applicability(candidate, requirement)
    assert eval_res["state"] == ApplicabilityState.NOT_APPLICABLE.value
    assert not eval_res["is_applicable"]
    assert "1100 V" in eval_res["rejection_reason"]


def test_lifecycle_supersession_resolution():
    """Verify older superseded standard is upgraded to active edition."""
    gate = LifecycleGate()
    # Contemporary evaluation date: 2025-01-01
    res = gate.resolve_edition("IS 13947 (Part 2):1993", evaluation_date="2025-01-01")
    assert res["is_superseded"]
    assert res["recommended_edition"] == "IS/IEC 60947 (Part 2):2016"


def test_lifecycle_amendments_tracking():
    """Verify active amendments are attached to the resolved edition."""
    gate = LifecycleGate()
    res = gate.resolve_edition("IS 694:2010")
    assert not res["is_superseded"]
    assert len(res["applicable_amendments"]) == 2
    assert "Amendment 1 (2015)" in res["amendment_notes"]


def test_regulatory_gate_qco_mandate():
    """Verify mandatory QCO is correctly recognized for regulated standards."""
    gate = RegulatoryGate()
    res = gate.evaluate_regulatory_status("IS 7098 (Part 2):2011")
    assert res["regulatory_state"] == RegulatoryState.MANDATORY_CONFIRMED.value
    assert res["is_mandatory"]
    assert "Quality Control" in res["qco_order"]

    # Unregulated standard gets safe fallback
    res_unknown = gate.evaluate_regulatory_status("IS 99999:2099")
    assert res_unknown["regulatory_state"] == RegulatoryState.MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES.value
    assert not res_unknown["is_mandatory"]


def test_end_to_end_recommendation_pipeline(mini_graph):
    """Verify full pipeline produces an evidence-grounded recommendation."""
    engine = StandSpecRecommendationEngine(mini_graph)

    query = "Procurement of 11 kV 3 x 300 sq.mm crosslinked polyethylene (XLPE) insulated power cable"
    decision = engine.recommend(query, evaluation_date="2025-06-01")

    assert decision["decision_state"] == "PRIMARY_RECOMMENDATION_AVAILABLE"
    assert decision["primary_recommendation"] is not None
    assert decision["primary_recommendation"]["standard_designation"] == "IS 7098 (Part 2):2011"
    assert decision["primary_recommendation"]["regulatory"]["is_mandatory"]
    assert len(decision["allied_standards"]) >= 1
    # Check IS 1554 was rejected
    rejected_desigs = [r["designation"] for r in decision["rejected_candidates"]]
    assert "IS 1554 (Part 1):1988" in rejected_desigs


def test_applicability_power_supply_transformer_exclusion():
    """Verify IS/IEC 61558 is excluded for 500 MVA grid power transformers."""
    engine = TechnicalApplicabilityEngine()
    candidate = {"designation": "IS/IEC 61558 (Part 1):1997", "title": "Safety of power transformers, power supply units"}
    requirement = {"raw_text": "500 MVA 400 kV autotransformer for grid substation"}

    eval_res = engine.evaluate_applicability(candidate, requirement)
    assert eval_res["state"] == ApplicabilityState.NOT_APPLICABLE.value
    assert not eval_res["is_applicable"]
    assert "IS/IEC 61558 is limited to small" in eval_res["rejection_reason"]


def test_family_series_graph_expansion():
    """Verify graph expander discovers Part 1 base standard from sibling Part 3."""
    from src.retrieval.graph_expansion import GraphCandidateExpander
    graph = {
        "nodes": [
            {"id": "IS 2026 (Part 1):2011", "family": "IS", "base_number": "2026", "part": "1", "title": "Part 1 General"},
            {"id": "IS 2026 (Part 3):2018", "family": "IS", "base_number": "2026", "part": "3", "title": "Part 3 Insulation"},
        ],
        "edges": []
    }
    expander = GraphCandidateExpander(graph)
    seeds = [{"designation": "IS 2026 (Part 3):2018", "score": 10.0}]
    expanded = expander.expand(seeds, top_k=5)
    expanded_ids = [c["designation"] for c in expanded]
    assert "IS 2026 (Part 1):2011" in expanded_ids


def test_regulatory_gate_glass_qco():
    """Verify IS 14900 transparent float glass QCO is recognized as mandatory."""
    gate = RegulatoryGate()
    res = gate.evaluate_regulatory_status("IS 14900:2018")
    assert res["regulatory_state"] == RegulatoryState.MANDATORY_CONFIRMED.value
    assert res["is_mandatory"]
    assert "Float Glass" in res["qco_order"]


def test_out_of_domain_abstention_bananas(mini_graph):
    """Engine must safely abstain with OUTSIDE_PROTOTYPE_COVERAGE or NO_CONFIDENT_MATCH on out-of-domain bananas query."""
    engine = StandSpecRecommendationEngine(mini_graph)
    res = engine.recommend("Supply of industrial bananas for food processing facility")
    assert res["decision_state"] in ("OUTSIDE_PROTOTYPE_COVERAGE", "NO_CONFIDENT_MATCH")
    assert res["primary_recommendation"] is None


def test_out_of_domain_abstention_satellite(mini_graph):
    """Engine must safely abstain with OUTSIDE_PROTOTYPE_COVERAGE or NO_CONFIDENT_MATCH on satellite Ku-band query."""
    engine = StandSpecRecommendationEngine(mini_graph)
    res = engine.recommend("satellite ground station Ku-band 14 GHz equipment")
    assert res["decision_state"] in ("OUTSIDE_PROTOTYPE_COVERAGE", "NO_CONFIDENT_MATCH")
    assert res["primary_recommendation"] is None


def test_out_of_domain_abstention_mri(mini_graph):
    """Engine must safely abstain with OUTSIDE_PROTOTYPE_COVERAGE or NO_CONFIDENT_MATCH on hospital MRI query."""
    engine = StandSpecRecommendationEngine(mini_graph)
    res = engine.recommend("hospital MRI 1.5 T superconducting magnet system")
    assert res["decision_state"] in ("OUTSIDE_PROTOTYPE_COVERAGE", "NO_CONFIDENT_MATCH")
    assert res["primary_recommendation"] is None


