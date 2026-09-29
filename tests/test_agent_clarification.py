"""
Tests for StandSpec AI Clarification Engine (Phase P1-F Section 18 & 45)
Verifies:
1. Bare / underspecified queries trigger targeted clarification requests.
2. Structured clarification reasons (MISSING_VOLTAGE, MISSING_CAPACITY, MISSING_APPLICATION).
3. Searchable queries do NOT trigger unnecessary clarifications.
"""

import pytest
from src.agent.agent import StandSpecAgent


@pytest.fixture(scope="module")
def agent():
    return StandSpecAgent.from_release()


def test_clarification_on_bare_cable_query(agent):
    """Verify bare 'Supply cable' query asks for voltage and installation context."""
    res = agent.answer("Supply cable", mode="offline")

    assert res["decision_state"] == "CLARIFICATION_REQUIRED"
    assert res["primary_recommendation"] is None
    assert res["clarification_category"] == "MISSING_VOLTAGE"
    assert len(res["clarifications_needed"]) > 0
    question = res["clarifications_needed"][0].lower()
    assert "voltage" in question or "material" in question


def test_clarification_on_bare_transformer_query(agent):
    """Verify bare 'Need transformer' query asks for capacity and voltage ratio."""
    res = agent.answer("Need transformer", mode="offline")

    assert res["decision_state"] == "CLARIFICATION_REQUIRED"
    assert res["primary_recommendation"] is None
    assert res["clarification_category"] == "MISSING_CAPACITY"
    assert len(res["clarifications_needed"]) > 0
    question = res["clarifications_needed"][0].lower()
    assert "capacity" in question or "voltage" in question


def test_clarification_on_bare_pipe_query(agent):
    """Verify bare 'Need pipe' query asks for pipe material, diameter, and application."""
    res = agent.answer("Need pipe", mode="offline")

    assert res["decision_state"] == "CLARIFICATION_REQUIRED"
    assert res["primary_recommendation"] is None
    assert res["clarification_category"] == "MISSING_APPLICATION"
    assert len(res["clarifications_needed"]) > 0
    question = res["clarifications_needed"][0].lower()
    assert "material" in question or "application" in question


def test_no_clarification_on_fully_specified_query(agent):
    """Verify that a specific, well-bounded query proceeds to recommendation without blocking."""
    query = "Supply of 1.1 kV XLPE insulated three-core power cables"
    res = agent.answer(query, mode="offline")

    assert res["decision_state"] == "PRIMARY_RECOMMENDATION_AVAILABLE"
    assert res["primary_recommendation"] is not None
