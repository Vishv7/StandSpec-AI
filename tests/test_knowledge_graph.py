"""
Tests for Standards Knowledge Graph Builder (Layer 1 -> Knowledge Graph).
Verifies node and edge creation, obligation assignment, dual-numbering linking,
and connected component computation.
"""

import json
from pathlib import Path
import pytest

from scripts.build_knowledge_graph import (
    build_graph_from_html,
    compute_graph_statistics,
    derive_obligation,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_obligation_mapping():
    """Verify obligation mapping conforms to RELATIONSHIP_TAXONOMY.md."""
    assert derive_obligation("normative_reference") == "MANDATORY"
    assert derive_obligation("test_method") == "MANDATORY"
    assert derive_obligation("safety_reference") == "MANDATORY"
    assert derive_obligation("dual_numbering") == "INFORMATIVE"
    assert derive_obligation("used_in_conjunction_with") == "CONDITIONAL"
    assert derive_obligation("related_to") == "RELATED"
    assert derive_obligation("unknown_rel") == "UNKNOWN"


def test_build_graph_from_fixtures(tmp_path):
    """Build graph from fixture HTML files and verify nodes and edges."""
    graph = build_graph_from_html(FIXTURES_DIR)
    
    assert graph["graph_version"] in ("1.0", "1.2.0", "1.2.1")
    assert graph["nodes_count"] > 0
    assert graph["edges_count"] > 0
    
    node_ids = {n["id"] for n in graph["nodes"]}
    # Check that known fixture standard nodes exist
    assert any("19901" in nid for nid in node_ids)
    
    for edge in graph["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids
        assert "relationship" in edge
        assert "relationship_obligation" in edge
        assert edge["source_tier"] == 1
        assert edge["edge_type"] == "DIRECT"
        assert edge["confidence"] >= 0.5


def test_compute_graph_statistics():
    """Verify graph statistics calculation."""
    sample_graph = {
        "nodes": [
            {"id": "IS 100", "node_type": "INDIAN_STANDARD"},
            {"id": "IS 200", "node_type": "INDIAN_STANDARD"},
            {"id": "ISO 300", "node_type": "EXTERNAL_STANDARD"},
        ],
        "edges": [
            {
                "source": "IS 100",
                "target": "IS 200",
                "relationship": "normative_reference",
                "relationship_obligation": "MANDATORY",
            },
            {
                "source": "IS 100",
                "target": "ISO 300",
                "relationship": "dual_numbering",
                "relationship_obligation": "INFORMATIVE",
            },
        ],
    }
    stats = compute_graph_statistics(sample_graph)
    assert stats["total_nodes"] == 3
    assert stats["total_edges"] == 2
    assert stats["relationship_distribution"]["normative_reference"] == 1
    assert stats["relationship_distribution"]["dual_numbering"] == 1
    assert stats["obligation_distribution"]["MANDATORY"] == 1
    assert stats["obligation_distribution"]["INFORMATIVE"] == 1
    assert stats["connected_components_count"] == 1
