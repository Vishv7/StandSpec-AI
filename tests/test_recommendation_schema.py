"""
Tests for RecommendationResult Schema Compliance (P0-1 Contract).
Verifies that 100% of generated RecommendationResult objects strictly validate
against schemas/recommendation_result.schema.json (Draft 2020-12).
"""

import json
from pathlib import Path
import pytest
import jsonschema

from src.recommendation.engine import StandSpecRecommendationEngine


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "recommendation_result.schema.json"
GRAPH_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "standards_graph.json"


@pytest.fixture(scope="module")
def recommendation_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def engine():
    if not GRAPH_PATH.exists():
        pytest.skip(f"Knowledge graph not found at {GRAPH_PATH}")
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    return StandSpecRecommendationEngine(graph)


def test_schema_valid_on_standard_queries(engine, recommendation_schema):
    """Test schema validation across diverse query types."""
    test_queries = [
        "Supply standard complying with IS 7098 Part 2 for 11 kV XLPE cable.",
        "High density polyethylene (HDPE) pipes for potable water supply, PE 100, PN 10, 110 mm OD",
        "Centrifugally cast (spun) iron pressure pipes for water, gas and sewage",
        "Supply of industrial bananas for food processing facility",
        "satellite ground station Ku-band 14 GHz equipment",
    ]

    for q in test_queries:
        result = engine.recommend(q)
        # Strict Draft 2020-12 validation
        jsonschema.validate(instance=result, schema=recommendation_schema)
        # Ensure no legacy disallowed properties
        assert "query_text" not in result
        assert "normalized_requirement" not in result
        assert "query" in result
        assert "normalized_requirements" in result
        assert "decision_state" in result
        assert "provenance" in result


def test_schema_valid_on_all_test_benchmark_cases(engine, recommendation_schema):
    """Verify that every test case in data/benchmarks/test.jsonl produces a valid schema object."""
    benchmark_path = Path(__file__).resolve().parent.parent / "data" / "benchmarks" / "test.jsonl"
    if not benchmark_path.exists():
        pytest.skip(f"Benchmark test file not found at {benchmark_path}")

    with open(benchmark_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    assert len(records) > 0

    for rec in records:
        raw_text = rec["query"]["raw_text"] if isinstance(rec["query"], dict) else rec["query"]
        result = engine.recommend(raw_text, query_id=rec.get("query_id"))
        jsonschema.validate(instance=result, schema=recommendation_schema)
