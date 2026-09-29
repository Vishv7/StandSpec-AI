"""
Tests for StandSpec AI Agent Orchestration (Phase P1-F Section 3, 4, 39, 40)
Verifies:
1. End-to-end agent loop (bounded steps <= 6)
2. Tool call audit traces
3. Critical adversarial test: uPVC pipes as per IS 1180 Part 1 veto
4. Multi-product query safe handling
5. Outside CED/ETD coverage detection
6. Offline deterministic mode
7. Mock LLM integration mode
"""

import json
import pytest
from src.agent.agent import StandSpecAgent
from src.llm.provider import MockLLMProvider


@pytest.fixture(scope="module")
def agent():
    return StandSpecAgent.from_release()


def test_agent_normal_procurement_query(agent):
    """Verify agent handles a standard procurement query and recommends a primary standard."""
    query = "Supply of 1.1 kV XLPE insulated three-core power cables"
    res = agent.answer(query, mode="offline")

    assert res["decision_state"] == "PRIMARY_RECOMMENDATION_AVAILABLE"
    assert res["primary_recommendation"] is not None
    assert "IS 7098" in res["primary_recommendation"]["designation"]
    assert res["confidence"] in ("HIGH", "MEDIUM")

    # Verify tool calls and audit metadata
    assert "agent_metadata" in res
    meta = res["agent_metadata"]
    assert meta["step_count"] <= StandSpecAgent.MAX_AGENT_STEPS
    assert meta["validator_status"] == "ACCEPT"
    assert "tool_calls" in res
    tool_names = [call["tool"] for call in res["tool_calls"]]
    assert "search_standards" in tool_names
    assert "check_applicability" in tool_names


def test_agent_critical_adversarial_upvc_is_1180(agent):
    """
    CRITICAL TEST (Section 40):
    Query: 'Supply of uPVC pipes as per IS 1180 Part 1'
    IS 1180 is for transformers, not uPVC pipes.
    Agent must NEVER recommend IS 1180 as primary!
    """
    query = "Supply of uPVC pipes as per IS 1180 Part 1"
    res = agent.answer(query, mode="offline")

    assert res["primary_recommendation"] is None
    assert res["decision_state"] in ("NO_CONFIDENT_MATCH", "EXPERT_REVIEW_REQUIRED")
    explanation = (res.get("natural_language_explanation") or "").lower()
    assert "is 1180" in explanation or "inapplicable" in explanation or "mismatch" in explanation


def test_agent_multi_product_query(agent):
    """Verify agent decomposes or flags multi-product queries (Section 44)."""
    query = "Supply cable, transformer, switchgear and metering panel for electrical substation"
    res = agent.answer(query, mode="offline")

    assert res["primary_recommendation"] is None
    assert res["decision_state"] == "MULTIPLE_POSSIBLE_STANDARDS"
    assert len(res["clarifications_needed"]) > 0
    assert any("multi-product" in c.lower() or "disjoint" in c.lower() for c in res["clarifications_needed"])


def test_agent_outside_prototype_coverage(agent):
    """Verify agent rejects queries outside CED and ETD scope (Section 20)."""
    query = "Supply of medical grade surgical gloves conforming to BIS"
    res = agent.answer(query, mode="offline")

    # Domain detected or unindexed candidates lead to OUTSIDE_PROTOTYPE_COVERAGE or NO_CONFIDENT_MATCH
    assert res["primary_recommendation"] is None
    assert res["decision_state"] in ("OUTSIDE_PROTOTYPE_COVERAGE", "NO_CONFIDENT_MATCH")


def test_agent_bounded_loop_constraints(agent):
    """Verify agent never exceeds MAX_AGENT_STEPS = 6."""
    query = "Supply of polyethylene pressure pipes, 110 mm, PN10, for potable water"
    res = agent.answer(query, mode="offline")

    meta = res["agent_metadata"]
    assert meta["step_count"] <= StandSpecAgent.MAX_AGENT_STEPS
    assert meta["search_rounds"] <= StandSpecAgent.MAX_SEARCH_ROUNDS
    assert meta["revision_rounds"] <= StandSpecAgent.MAX_REVISION_ROUNDS


def test_agent_with_mock_llm_provider(agent):
    """Verify agent functions under LLM_ASSISTED execution mode using MockLLMProvider."""
    canned_answer = json.dumps({
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 7098 (Part 1):2025",
            "title": ": Part 1 : 2025 Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables - Specification - Part 1 For Working Voltages up to and including 1 100 Volts",
            "reason": "Matches crosslinked polyethylene (XLPE) material and working voltage up to 1.1 kV.",
            "applicability_state": "APPLICABLE",
            "claim_level": "VERIFIED",
            "evidence_ids": ["EV_IS 7098 (Part 1):2025"],
            "matched_attributes": ["PRODUCT", "MATERIAL", "VOLTAGE"],
        },
        "alternative_standards": [],
        "review_candidate": None,
        "clarifications_needed": [],
        "confidence": "HIGH",
        "regulatory": {
            "state": "NOT_VERIFIED_IN_CURRENT_CORPUS",
            "statement": "Regulatory mandatory status was not verified in the current regulatory corpus.",
        },
        "natural_language_explanation": "Based on retrieved BIS evidence, IS 7098 (Part 1):2025 is the verified primary recommendation.",
    })
    mock_provider = MockLLMProvider(canned_responses={"Based ONLY on the retrieved BIS evidence": canned_answer})
    llm_agent = StandSpecAgent(engine=agent.engine, llm_provider=mock_provider)

    query = "Supply of 1.1 kV XLPE insulated three-core power cables"
    res = llm_agent.answer(query, mode="llm")

    assert res["agent_metadata"]["execution_mode"] == "LLM_ASSISTED"
    assert res["agent_metadata"]["validator_status"] == "ACCEPT"
    assert res["decision_state"] == "PRIMARY_RECOMMENDATION_AVAILABLE"
    assert "IS 7098 (Part 1)" in res["primary_recommendation"]["designation"]
