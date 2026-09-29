"""
Production Query Independence Tests — StandSpec AI (Phase P1-E Section 26).
Verifies that:
- OpenWorldQuery contract enforces isolation and accepts unseen procurement queries.
- StandSpecRecommendationEngine works with arbitrary raw queries.
- Engine returns a structured RecommendationResult without requiring benchmark files, IDs, or gold labels.
- Distinguishes SEARCHABLE vs RECOMMENDABLE queries.
"""

import json
from pathlib import Path
import pytest
from unittest.mock import patch

from src.query.open_world_contract import OpenWorldQuery
from src.recommendation.engine import StandSpecRecommendationEngine

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def engine():
    graph_path = PROJECT_ROOT / "data" / "processed" / "standards_graph.json"
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)
    return StandSpecRecommendationEngine(graph)


def test_open_world_query_contract_validates_isolation():
    """Ensure benchmark keys are strictly rejected by the OpenWorldQuery contract."""
    with pytest.raises(ValueError, match="Benchmark isolation violation"):
        OpenWorldQuery(
            raw_text="Procure copper wire",
            requirements={"benchmark_id": "TEST_001"},
        )

    with pytest.raises(ValueError, match="Cannot create OpenWorldQuery from benchmark data"):
        OpenWorldQuery.from_dict({
            "raw_text": "Procure copper wire",
            "gold_standards": [{"standard_designation": "IS 694:2010"}],
        })


def test_open_world_query_searchable_vs_recommendable():
    """Verify SEARCHABLE vs RECOMMENDABLE behavior for partially specified queries."""
    # Under-specified query is SEARCHABLE (for candidate retrieval) but NOT RECOMMENDABLE (for primary)
    underspec = OpenWorldQuery(
        raw_text="Supply of cable",
        procurement_object="cable",
        query_sufficiency="UNDER_SPECIFIED",
    )
    assert underspec.is_searchable is True
    assert underspec.is_recommendable is False

    # Fully specified query is both
    full = OpenWorldQuery(
        raw_text="Supply of 33 kV 3-core XLPE power cable for underground installation",
        procurement_object="power cable",
        requirements={"product": {"value": "cable"}, "voltage": {"value": "33 kV"}},
        query_sufficiency="SUFFICIENT",
    )
    assert full.is_searchable is True
    assert full.is_recommendable is True

    # Empty text is neither
    with pytest.raises(ValueError):
        OpenWorldQuery(raw_text="")


def test_engine_processes_completely_unseen_query_without_benchmark(engine):
    """
    Test end-to-end recommendation on a completely new natural-language tender clause.
    Verifies that no benchmark file is touched and structured response is emitted.
    """
    unseen_query = (
        "Urgent procurement of single-core cross-linked polyethylene insulated "
        "heavy duty cables for municipal street lighting project, operating voltage 1100 V."
    )

    original_open = open

    def block_benchmark_reads(file, *args, **kwargs):
        file_str = str(file)
        if "data/benchmarks" in file_str or "data\\benchmarks" in file_str:
            raise PermissionError(f"Engine attempted to access benchmark file: {file_str}")
        return original_open(file, *args, **kwargs)

    with patch("builtins.open", side_effect=block_benchmark_reads):
        res = engine.recommend(unseen_query)

    assert res is not None
    assert "decision_state" in res
    assert "provenance" in res
    assert res["provenance"]["engine_version"] is not None
    assert res["normalized_requirements"]["query_id"] is not None
    assert res["normalized_requirements"]["query_id"].startswith("Q_")
    # Natural language explanation must be present
    assert "natural_language_explanation" in res
