"""
Tests for Supporting Context Pack Grounded in Graph Edges (P1-7, P1-12).
Verifies that supporting_context_pack is populated from verified graph edges
(test_methods, materials, installation_codes, normative_references).
"""

import json
from pathlib import Path
import pytest
import jsonschema

from src.recommendation.engine import StandSpecRecommendationEngine


@pytest.fixture
def mini_graph():
    return {
        "release_id": "test-graph-v1",
        "nodes": [
            {
                "id": "IS 7098 (Part 2):2011",
                "designation": "IS 7098 (Part 2):2011",
                "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables: Part 2 For Working Voltages From 3.3 kV Up to and Including 33 kV",
                "scope": "Prescribes requirements for XLPE cables 3.3 kV to 33 kV.",
                "candidate_status": "ELIGIBLE",
                "department": "ETD",
                "is_hydrated": True,
                "scope_evidence_available": True,
                "recommendation_ready": True,
                "publication_date": "2011-01-01",
                "lifecycle_status": "ACTIVE",
            },
            {
                "id": "IS 10810 (Part 53):1984",
                "designation": "IS 10810 (Part 53):1984",
                "title": "Methods of test for cables: Part 53 Flammability test",
                "scope": "Covers flammability testing of cables.",
                "candidate_status": "SUPPORTING_ONLY",
                "is_hydrated": True,
                "scope_evidence_available": True,
                "recommendation_ready": False,
            },
            {
                "id": "IS 8130:2013",
                "designation": "IS 8130:2013",
                "title": "Conductors for insulated electric cables and flexible cords",
                "scope": "Specifies conductors for insulated cables.",
                "candidate_status": "SUPPORTING_ONLY",
                "is_hydrated": True,
                "scope_evidence_available": True,
                "recommendation_ready": False,
            },
        ],
        "edges": [
            {
                "source": "IS 7098 (Part 2):2011",
                "target": "IS 10810 (Part 53):1984",
                "relationship": "test_method",
                "relationship_confidence_state": "HIGH",
            },
            {
                "source": "IS 7098 (Part 2):2011",
                "target": "IS 8130:2013",
                "relationship": "material_reference",
                "relationship_confidence_state": "HIGH",
            },
        ],
    }


def test_supporting_context_grounded_in_edges(mini_graph):
    """Verify context pack extracts IS 10810 and IS 8130 from explicit graph edges."""
    engine = StandSpecRecommendationEngine(mini_graph)
    res = engine.recommend("Supply standard complying with IS 7098 Part 2 for 11 kV XLPE cable.")

    assert res["decision_state"] == "PRIMARY_RECOMMENDATION_AVAILABLE"
    pack = res["supporting_context_pack"]
    assert isinstance(pack, dict)
    assert "IS 10810 (Part 53):1984" in pack["test_methods"]
    assert "IS 8130:2013" in pack["materials"]


def test_supporting_context_pack_schema_valid(mini_graph):
    """Verify supporting context pack validates against RecommendationResult schema."""
    engine = StandSpecRecommendationEngine(mini_graph)
    res = engine.recommend("Supply standard complying with IS 7098 Part 2 for 11 kV XLPE cable.")

    schema_path = Path("schemas/recommendation_result.schema.json")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    jsonschema.validate(instance=res, schema=schema)
