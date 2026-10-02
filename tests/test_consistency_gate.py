"""
Tests for RequirementConsistencyGate — StandSpec AI (Phase 2 / Mentor Review Part 3)
Verifies:
1. Within-domain parameter contradictions (cement grades, steel grades, meter technologies, pipe applications, cable installations, voltage classes).
2. Cross-domain impossible product collisions (pipes + transformers/33kV, cables + cement, meters + rebar, etc.).
3. Clean, consistent procurement queries pass without contradictions.
4. StandSpecRecommendationEngine blocks contradictory queries, sets decision_state to INSUFFICIENT_INFORMATION, primary_recommendation to None, and outputs actionable clarification guidance.
"""

import pytest
from src.recommendation.consistency_gate import RequirementConsistencyGate, ConsistencyCheckResult
from src.recommendation.engine import StandSpecRecommendationEngine


def test_cement_grade_contradictions():
    """Conflicting cement grades specified in same requirement must be detected."""
    res = RequirementConsistencyGate.check("Supply of 43 grade and 53 grade cement for structural columns")
    assert not res.is_consistent
    assert len(res.contradictions) == 1
    assert res.contradictions[0].conflict_type == "CEMENT_GRADE_CONFLICT"
    assert "43 Grade" in res.contradictions[0].parameters
    assert "53 Grade" in res.contradictions[0].parameters
    assert "Specify exactly one OPC cement grade" in res.clarification_message


def test_steel_grade_contradictions():
    """Conflicting reinforcement steel grades specified simultaneously must be detected."""
    res = RequirementConsistencyGate.check("Procurement of high strength deformed bars grade Fe 415 and Fe 500D for RCC slab")
    assert not res.is_consistent
    assert len(res.contradictions) == 1
    assert res.contradictions[0].conflict_type == "STEEL_GRADE_CONFLICT"
    assert "Fe 415" in res.contradictions[0].parameters
    assert "Fe 500" in res.contradictions[0].parameters


def test_pipe_material_contradictions():
    """Conflicting pipe materials for single pipe requirement must be detected."""
    res = RequirementConsistencyGate.check("Supply of HDPE pipe and uPVC pipe for underground main conduit")
    assert not res.is_consistent
    assert any(c.conflict_type == "PIPE_MATERIAL_CONFLICT" for c in res.contradictions)


def test_pipe_application_contradictions():
    """Potable water supply vs sewage/drainage application conflict must be detected."""
    res = RequirementConsistencyGate.check("HDPE pipes for potable drinking water and sewage drainage line")
    assert not res.is_consistent
    assert any(c.conflict_type == "APPLICATION_CONFLICT" for c in res.contradictions)


def test_meter_technology_contradictions():
    """Static electronic vs electromechanical induction meter conflict must be detected."""
    res = RequirementConsistencyGate.check("Single phase static electronic induction energy meter")
    assert not res.is_consistent
    assert any(c.conflict_type == "METER_TECHNOLOGY_CONFLICT" for c in res.contradictions)


def test_cable_installation_contradictions():
    """Aerial bunched overhead vs underground buried cable conflict must be detected."""
    res = RequirementConsistencyGate.check("Aerial bunched cable for underground trench laying")
    assert not res.is_consistent
    assert any(c.conflict_type == "INSTALLATION_CONFLICT" for c in res.contradictions)


def test_voltage_class_contradictions():
    """Low voltage (<= 1.1 kV) specified with 33 kV high voltage must be detected."""
    res = RequirementConsistencyGate.check("Low voltage LT cable for 33 kV power transmission line")
    assert not res.is_consistent
    assert any(c.conflict_type == "VOLTAGE_CLASS_CONFLICT" for c in res.contradictions)


@pytest.mark.parametrize("query,expected_conflict", [
    ("HDPE pipe with 33kV XLPE insulation", "CROSS_DOMAIN_PIPE_ELECTRICAL"),
    ("Supply of 33kV XLPE cable with OPC 53 cement mix", "CROSS_DOMAIN_CABLE_CEMENT"),
    ("Static energy meter with Fe 500D TMT rebar reinforcement", "CROSS_DOMAIN_METER_STEEL"),
    ("TMT rebar grade Fe 500 with LED luminaire fixtures", "CROSS_DOMAIN_STEEL_LIGHTING"),
    ("Distribution transformer 100 kVA with cast iron pipe for water supply", "CROSS_DOMAIN_TRANSFORMER_PLUMBING"),
])
def test_cross_domain_contradictions(query, expected_conflict):
    """Cross-domain product collisions must be detected and blocked."""
    res = RequirementConsistencyGate.check(query)
    assert not res.is_consistent
    assert any(c.conflict_type == expected_conflict for c in res.contradictions)


@pytest.mark.parametrize("query", [
    "Supply of 11 kV 3-core 185 sq mm XLPE insulated aluminium power cables",
    "Procurement of 53 grade ordinary Portland cement for bridge construction",
    "HDPE pipes conforming to IS 4984 for potable water distribution",
    "Static watt-hour energy meter Class 1.0 for AC active energy measurement",
    "TMT steel reinforcement bars grade Fe 500D conforming to IS 1786",
])
def test_consistent_procurement_queries(query):
    """Standard, coherent procurement queries must pass consistency check without contradictions."""
    res = RequirementConsistencyGate.check(query)
    assert res.is_consistent
    assert len(res.contradictions) == 0
    assert res.abstention_reason is None
    assert res.clarification_message is None


def test_engine_blocks_contradictory_query():
    """Engine recommend() must abstain with CONTRADICTORY_SPECIFICATIONS and primary_recommendation=None on contradictions."""
    engine = StandSpecRecommendationEngine({"nodes": [], "edges": []})

    # Within-domain contradiction
    res1 = engine.recommend("Supply of 43 grade and 53 grade cement for structural columns")
    assert res1["decision_state"] == "CONTRADICTORY_SPECIFICATIONS"
    assert res1["primary_recommendation"] is None
    assert len(res1["contradictions"]) >= 1
    assert res1["clarification_prompt"] is not None
    assert "Specify exactly one OPC cement grade" in res1["clarification_prompt"]

    # Decision trace must record CONFLICT at query_sufficiency stage
    sufficiency_step = next((s for s in res1["decision_trace"] if s["stage"] == "query_sufficiency"), None)
    assert sufficiency_step is not None
    assert sufficiency_step["status"] == "CONFLICT"
    assert sufficiency_step["blocking"] is True

    # Cross-domain contradiction
    res2 = engine.recommend("HDPE pipe with 33kV XLPE insulation")
    assert res2["decision_state"] == "CONTRADICTORY_SPECIFICATIONS"
    assert res2["primary_recommendation"] is None
    assert len(res2["contradictions"]) >= 1
    assert "civil piping and electrical equipment" in res2["clarification_prompt"]
