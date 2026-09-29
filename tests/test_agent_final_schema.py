"""
Tests for StandSpec AI Agent Final Output Schema Validation (Phase P1-F Section 14, 24, 25).
Verifies:
1. Agent answers strictly conform to schemas/agent_final_answer.schema.json.
2. Validates across all decision states:
   - PRIMARY_RECOMMENDATION_AVAILABLE
   - NO_CONFIDENT_MATCH
   - MULTIPLE_POSSIBLE_STANDARDS
   - OUTSIDE_PROTOTYPE_COVERAGE
   - CLARIFICATION_REQUIRED
3. Verifies schema compliance of tool actions against schemas/agent_action.schema.json.
"""

import json
from pathlib import Path
import pytest
import jsonschema
from src.agent.agent import StandSpecAgent


FINAL_ANSWER_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "agent_final_answer.schema.json"
ACTION_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "agent_action.schema.json"


@pytest.fixture(scope="module")
def agent_final_answer_schema():
    with open(FINAL_ANSWER_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def agent_action_schema():
    with open(ACTION_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def agent():
    return StandSpecAgent.from_release()


def test_schema_valid_primary_recommendation(agent, agent_final_answer_schema):
    """Verify primary recommendation output validates against agent_final_answer.schema.json."""
    query = "Supply of 1.1 kV XLPE insulated three-core power cables"
    res = agent.answer(query, mode="offline")

    assert res["decision_state"] == "PRIMARY_RECOMMENDATION_AVAILABLE"
    jsonschema.validate(instance=res, schema=agent_final_answer_schema)


def test_schema_valid_adversarial_mismatch(agent, agent_final_answer_schema):
    """Verify adversarial mismatch output validates against agent_final_answer.schema.json."""
    query = "Supply of uPVC pipes as per IS 1180 Part 1"
    res = agent.answer(query, mode="offline")

    assert res["decision_state"] in ("NO_CONFIDENT_MATCH", "EXPERT_REVIEW_REQUIRED")
    jsonschema.validate(instance=res, schema=agent_final_answer_schema)


def test_schema_valid_multi_product(agent, agent_final_answer_schema):
    """Verify multi-product query output validates against agent_final_answer.schema.json."""
    query = "Supply cable, transformer, switchgear and metering panel for electrical substation"
    res = agent.answer(query, mode="offline")

    assert res["decision_state"] == "MULTIPLE_POSSIBLE_STANDARDS"
    jsonschema.validate(instance=res, schema=agent_final_answer_schema)


def test_schema_valid_outside_coverage(agent, agent_final_answer_schema):
    """Verify outside prototype coverage output validates against agent_final_answer.schema.json."""
    query = "Supply of medical grade surgical gloves conforming to BIS"
    res = agent.answer(query, mode="offline")

    assert res["decision_state"] in ("OUTSIDE_PROTOTYPE_COVERAGE", "NO_CONFIDENT_MATCH")
    jsonschema.validate(instance=res, schema=agent_final_answer_schema)


def test_schema_valid_clarification_required(agent, agent_final_answer_schema):
    """Verify clarification required output validates against agent_final_answer.schema.json."""
    query = "cable"
    res = agent.answer(query, mode="offline")

    assert res["decision_state"] == "CLARIFICATION_REQUIRED"
    jsonschema.validate(instance=res, schema=agent_final_answer_schema)


def test_agent_action_schema_valid(agent_action_schema):
    """Verify tool action definitions strictly conform to schemas/agent_action.schema.json."""
    actions = [
        {
            "action": "TOOL_CALL",
            "tool": "search_standards",
            "arguments": {"query": "XLPE cables", "top_k": 5},
            "thought": "Retrieve candidate standards for low voltage XLPE cables",
        },
        {
            "action": "ASK_CLARIFICATION",
            "question": "Please specify voltage level and insulation type.",
            "clarification_reason": "MISSING_VOLTAGE",
        },
        {
            "action": "FINAL_PROPOSAL",
            "thought": "Candidate IS 7098 (Part 1):2025 verified by scope and active lifecycle.",
            "answer": {
                "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
                "primary_recommendation": {
                    "designation": "IS 7098 (Part 1):2025",
                },
            },
        },
    ]

    for action in actions:
        jsonschema.validate(instance=action, schema=agent_action_schema)
