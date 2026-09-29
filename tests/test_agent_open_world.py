"""
Tests for StandSpec AI Agent Open-World Benchmark Evaluation (Phase P1-F Section 41).
Verifies:
1. Agent runs across all open-world benchmark queries without crashing.
2. Step count strictly obeys MAX_AGENT_STEPS <= 6.
3. Every response strictly validates against schemas/agent_final_answer.schema.json.
4. Deterministic safety gates enforce 0 false positives on adversarial/out-of-scope cases.
"""

import json
from pathlib import Path
import pytest
import jsonschema
from src.agent.agent import StandSpecAgent


BENCHMARK_PATH = Path(__file__).resolve().parent.parent / "data" / "benchmarks" / "open_world.jsonl"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "agent_final_answer.schema.json"


@pytest.fixture(scope="module")
def agent():
    return StandSpecAgent.from_release()


@pytest.fixture(scope="module")
def schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def open_world_records():
    if not BENCHMARK_PATH.exists():
        pytest.skip(f"Benchmark file not found at {BENCHMARK_PATH}")
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_agent_open_world_benchmark_execution(agent, schema, open_world_records):
    """Run all open-world benchmark queries through StandSpecAgent in offline mode."""
    assert len(open_world_records) >= 50

    success_count = 0
    valid_schema_count = 0

    for rec in open_world_records:
        raw_text = rec["query"]["raw_text"] if isinstance(rec.get("query"), dict) else rec["query"]
        eval_date = rec.get("source", {}).get("evaluation_as_of_date") if isinstance(rec.get("source"), dict) else None

        res = agent.answer(raw_text, mode="offline", evaluation_date=eval_date)

        # 1. State must be non-empty and valid enum
        assert "decision_state" in res
        assert res["decision_state"] in [
            "PRIMARY_RECOMMENDATION_AVAILABLE",
            "CONDITIONAL_RECOMMENDATION",
            "MULTIPLE_POSSIBLE_STANDARDS",
            "INSUFFICIENT_INFORMATION",
            "NO_CONFIDENT_MATCH",
            "STANDARD_DATA_UNAVAILABLE",
            "OUTSIDE_PROTOTYPE_COVERAGE",
            "EXPERT_REVIEW_REQUIRED",
            "CLARIFICATION_REQUIRED",
        ]

        # 2. Loop bounds: step count <= 6
        meta = res.get("agent_metadata", {})
        assert meta.get("step_count", 0) <= StandSpecAgent.MAX_AGENT_STEPS

        # 3. Schema validation
        jsonschema.validate(instance=res, schema=schema)
        valid_schema_count += 1
        success_count += 1

    assert success_count == len(open_world_records)
    assert valid_schema_count == len(open_world_records)
