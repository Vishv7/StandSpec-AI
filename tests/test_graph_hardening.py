"""
Tests for Knowledge Graph Hardening (Gate P0-7 / Stream B).
Verifies obligation decoupling, edge origin taxonomy, verification flags,
node hydration policy, duplicate edge prevention, and metadata envelope.
"""

from pathlib import Path
import pytest

from scripts.build_knowledge_graph import (
    build_graph_from_html,
    compute_graph_statistics,
    derive_obligation,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_derive_obligation_decoupling():
    """Verify obligation is decoupled from relationship and driven by structural context."""
    # 1. Without context: falls back to baseline taxonomy mapping
    assert derive_obligation("normative_reference") == "MANDATORY"
    assert derive_obligation("dual_numbering") == "INFORMATIVE"
    assert derive_obligation("used_in_conjunction_with") == "CONDITIONAL"
    assert derive_obligation("related_to") == "RELATED"
    assert derive_obligation("unknown_rel") == "UNKNOWN"

    # 2. Context with conditional marker overrides normative_reference to CONDITIONAL
    ctx_conditional = {
        "text": "Applicable only if specified by purchaser in the tender contract",
        "source_section": "REFERENCES",
        "extraction_method": "html_table_row",
    }
    assert derive_obligation("normative_reference", ctx_conditional) == "CONDITIONAL"

    # 3. Context in Informative Annex or marked Informative overrides to INFORMATIVE
    ctx_informative = {
        "text": "Listed for information only in Annex B (informative)",
        "source_section": "ANNEX_B_INFORMATIVE",
        "extraction_method": "html_table_row",
    }
    assert derive_obligation("normative_reference", ctx_informative) == "INFORMATIVE"

    # 4. Conjunction reference with explicit 'shall' becomes MANDATORY
    ctx_mandatory_conjunction = {
        "text": "This standard shall be read in conjunction with IS 302 (Part 1).",
        "source_section": "NATIONAL FOREWORD",
        "extraction_method": "prose_phrase_scan",
    }
    assert derive_obligation("used_in_conjunction_with", ctx_mandatory_conjunction) == "MANDATORY"

    # 5. Conjunction reference without 'shall' defaults to CONDITIONAL
    ctx_default_conjunction = {
        "text": "May be used in conjunction with IS 1234 when applicable.",
        "source_section": "NATIONAL FOREWORD",
        "extraction_method": "prose_phrase_scan",
    }
    assert derive_obligation("used_in_conjunction_with", ctx_default_conjunction) == "CONDITIONAL"

    # 6. Informative relationship types remain INFORMATIVE regardless of modal words in text
    ctx_dual = {
        "text": "IS 1234 : 2024 / ISO 5678 : 2024 - shall be followed",
        "source_section": "REFERENCES",
    }
    assert derive_obligation("dual_numbering", ctx_dual) == "INFORMATIVE"
    assert derive_obligation("equivalent_to", ctx_dual) == "INFORMATIVE"
    assert derive_obligation("supersedes", ctx_dual) == "INFORMATIVE"


def test_graph_node_hydration_and_recommendation_eligibility():
    """Verify that only primary standards with cached previews are hydrated and recommendation-eligible."""
    graph = build_graph_from_html(FIXTURES_DIR)

    hydrated_nodes = [n for n in graph["nodes"] if n["is_hydrated"]]
    unhydrated_nodes = [n for n in graph["nodes"] if not n["is_hydrated"]]

    # We must have both hydrated primary standards and unhydrated target references
    assert len(hydrated_nodes) > 0
    assert len(unhydrated_nodes) > 0

    # Hydrated standards must have cached preview flag True and preview_id
    for hn in hydrated_nodes:
        assert hn["has_cached_preview"] is True
        assert hn["preview_id"] is not None
        if hn["node_type"] == "INDIAN_STANDARD":
            if hn.get("candidate_status") == "SUPPORTING_ONLY":
                assert hn["is_recommendation_eligible"] is False
            else:
                assert hn["is_recommendation_eligible"] is True
        else:
            assert hn["is_recommendation_eligible"] is False

    # Unhydrated targets (stubs) must NEVER be recommendation-eligible
    for un in unhydrated_nodes:
        assert un["has_cached_preview"] is False
        assert un["is_recommendation_eligible"] is False


def test_graph_edge_verification_and_origin_taxonomy():
    """Verify edge origin, verification flags, and confidence calibration."""
    graph = build_graph_from_html(FIXTURES_DIR)

    for edge in graph["edges"]:
        # Origin taxonomy
        assert edge["edge_origin"] == "DIRECT"
        assert edge["edge_type"] == "DIRECT"
        assert edge["source_extracted"] is True

        # Verification booleans and statuses
        assert isinstance(edge["source_page_identity_verified"], bool)
        assert isinstance(edge["relationship_verified"], bool)
        assert edge["edge_verification_status"] in ("SELF_IDENTIFIED_ONLY", "VERIFIED", "UNRESOLVED")
        assert isinstance(edge["page_self_identified"], bool)
        assert isinstance(edge["manifest_identity_verified"], bool)

        # Confidence calibration rules
        if edge["relationship_verified"] and edge["source_page_identity_verified"]:
            assert edge["confidence"] >= 0.85
        elif edge["relationship"] == "related_to":
            assert edge["confidence"] == 0.5


def test_graph_duplicate_edge_prevention():
    """Verify that duplicate edges (source, target, relationship) are strictly prevented."""
    graph = build_graph_from_html(FIXTURES_DIR)
    edge_triplets = [(e["source"], e["target"], e["relationship"]) for e in graph["edges"]]
    assert len(edge_triplets) == len(set(edge_triplets)), "Duplicate edges detected in graph!"


def test_graph_metadata_envelope():
    """Verify top-level metadata envelope and counts."""
    graph = build_graph_from_html(FIXTURES_DIR)

    assert graph["graph_version"] in ("1.2.0", "1.2.1")
    assert graph["schema_version"] in ("1.2", "1.2.0")
    assert graph["parser_version"] in ("1.2.0", "1.2.1")
    assert graph["release_id"] == "STANDSPEC_KG_2026_09"
    assert "built_at" in graph
    assert graph["source_type"] in ("preview_html", "html_dir")

    assert graph["nodes_count"] == len(graph["nodes"])
    assert graph["edges_count"] == len(graph["edges"])
    assert graph["hydrated_nodes_count"] + graph["unhydrated_nodes_count"] == graph["nodes_count"]
    assert graph["direct_edges_count"] + graph["inferred_edges_count"] == graph["edges_count"]


def test_graph_coordinate_details():
    """Verify extraction details capture coordinates on edges."""
    graph = build_graph_from_html(FIXTURES_DIR)
    
    table_edges = [e for e in graph["edges"] if e["extraction_details"]["extraction_method"] == "html_table_row"]
    assert len(table_edges) > 0
    for te in table_edges:
        det = te["extraction_details"]
        assert "source_section" in det
        assert "continuation_resolved" in det
        assert "table_index" in det
        assert "row_index" in det
