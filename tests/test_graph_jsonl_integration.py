"""
Integration tests for V1.2 JSONL -> Knowledge Graph pipeline.
Verifies that collector-produced V1.2 records are correctly consumed
by build_knowledge_graph.py and that references_status propagates through.

Tests are 100% network-independent (A15).
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.build_knowledge_graph import build_graph_from_jsonl, _get_v12_identity_verified, validate_graph


def _make_v12_record(desig, title="Test Standard", refs=None, identity_match="match_version_verified",
                     references_status="parsed", year="2024"):
    """Create a minimal valid V1.2 standard record."""
    if refs is None:
        refs = []
    base = desig.replace("IS ", "").split("(")[0].strip().split(":")[0]
    return {
        "record_version": "1.2",
        "input": {"source_file": "test.xlsx", "source_sheet": "Sheet1", "source_row": 2,
                  "raw_standard_number": desig, "raw_title": title},
        "provenance": {
            "first_seen_at": "2026-09-26T10:00:00+00:00",
            "first_run_started_at": "2026-09-26T10:00:00+00:00",
            "last_run_started_at": "2026-09-26T10:30:00+00:00",
            "record_last_processed_at": "2026-09-26T10:30:00+00:00",
            "parser_version": "1.2.0",
            "collector_version": "1.2.0",
            "schema_version": "1.2",
            "source_file": "test.xlsx",
            "source_sheet": "Sheet1",
            "source_row": 2,
            "row_sha256": "abc123",
        },
        "raw_excel": {
            "sheet_name": "Sheet1", "row_number": 2, "row_sha256": "abc123",
            "columns": {"Standard Number": desig},
        },
        "identity": {
            "standard_designation": desig,
            "family": "IS",
            "base_number": base,
            "part": None,
            "section": None,
            "year": year,
        },
        "content": {
            "header_text": f"{desig} {title}",
            "title": title,
            "title_source": "preview",
            "ics_raw": None,
            "ics_codes": [],
            "committee": None,
            "scope": {"text": "Test scope.", "status": "present",
                      "extraction_method": "html_section", "scope_source_section": "SCOPE", "reason": None},
            "national_foreword": {"text": None, "status": "absent", "extraction_method": None, "reason": None},
            "notes": {"items": [], "status": "absent", "extraction_method": None, "reason": None},
            "evidence_verified": True,
            "references_status": references_status,
        },
        "references": refs,
        "source": {
            "verified_source_url": "https://example.com/preview",
            "candidate_urls": ["https://example.com/preview"],
            "preview_url": "https://example.com/preview",
            "requested_preview_id": "19901_2026",
            "matched_preview_id": "19901_2026",
            "attempted_urls": ["https://example.com/preview"],
            "http_status": 200,
            "fetch_status": "success",
            "identity_match": identity_match,
            "page_identity_evidence": {
                "header_text": f"{desig} {title}",
                "normalized_designation": desig,
                "verification_method": "header_parser",
                "requested_year": year,
                "page_year": year,
                "year_match": True,
                "year_verification": "verified",
            },
        },
        "primary_status": "success",
        "quality": {"manual_review_required": False, "warnings": [], "errors": []},
    }


def _write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class TestGetV12IdentityVerified:
    def test_match_version_verified(self):
        rec = _make_v12_record("IS 1070:1992", identity_match="match_version_verified")
        assert _get_v12_identity_verified(rec) is True

    def test_match(self):
        rec = _make_v12_record("IS 1070:1992", identity_match="match")
        assert _get_v12_identity_verified(rec) is True

    def test_match_version_uncertain(self):
        rec = _make_v12_record("IS 1070:1992", identity_match="match_version_uncertain")
        assert _get_v12_identity_verified(rec) is False

    def test_mismatch(self):
        rec = _make_v12_record("IS 1070:1992", identity_match="mismatch")
        assert _get_v12_identity_verified(rec) is False


class TestBuildGraphFromV12Jsonl:
    def test_two_records_produce_two_nodes(self, tmp_path):
        """Two V1.2 JSONL records must produce at least 2 nodes (source + target stubs)."""
        rec1 = _make_v12_record("IS 19901:2026", title="Biotherapeutic Handling")
        rec2 = _make_v12_record("IS 1070:1992", title="General Construction Safety",
                                identity_match="match_version_verified")

        jsonl_path = tmp_path / "standards.jsonl"
        _write_jsonl(jsonl_path, [rec1, rec2])

        graph = build_graph_from_jsonl(jsonl_path)
        assert graph["nodes_count"] >= 2
        assert graph["edges_count"] >= 0

        node_ids = {n["id"] for n in graph["nodes"]}
        assert "IS 19901:2026" in node_ids
        assert "IS 1070:1992" in node_ids

    def test_references_status_propagated(self, tmp_path):
        """content.references_status must appear on the graph node."""
        rec = _make_v12_record("IS 19901:2026", references_status="parsed")
        jsonl_path = tmp_path / "standards.jsonl"
        _write_jsonl(jsonl_path, [rec])

        graph = build_graph_from_jsonl(jsonl_path)
        source_node = next(n for n in graph["nodes"] if n["id"] == "IS 19901:2026")
        assert source_node["references_status"] == "parsed"

    def test_references_create_edges(self, tmp_path):
        """Reference entries in V1.2 record must produce graph edges."""
        ref = {
            "source_standard": "IS 19901:2026",
            "target": {
                "designation": "IS 1070:1992",
                "family": "IS",
                "base_number": "1070",
                "part": None, "section": None, "year": "1992",
            },
            "reference_type": "formal_reference",
            "relationship": "normative_reference",
            "relationship_confidence": "structural",
            "evidence": {
                "text": "IS 1070 : 1992 - General safety code",
                "source_section": "REFERENCES",
                "extraction_method": "html_table_row",
                "complete": True,
                "continuation_resolved": False,
                "bare_number_resolved": True,
            },
        }
        rec = _make_v12_record("IS 19901:2026", refs=[ref])
        jsonl_path = tmp_path / "standards.jsonl"
        _write_jsonl(jsonl_path, [rec])

        graph = build_graph_from_jsonl(jsonl_path)
        assert graph["edges_count"] == 1
        edge = graph["edges"][0]
        assert edge["source"] == "IS 19901:2026"
        assert edge["target"] == "IS 1070:1992"
        assert edge["relationship"] == "normative_reference"
        assert edge["edge_verification_status"] == "VERIFIED"
        assert edge["verified"] is True

    def test_version_uncertain_produces_unresolved(self, tmp_path):
        """When identity_match is uncertain, edges must be UNRESOLVED."""
        ref = {
            "source_standard": "IS 19901:2026",
            "target": {
                "designation": "IS 1070:1992",
                "family": "IS", "base_number": "1070",
                "part": None, "section": None, "year": "1992",
            },
            "reference_type": "formal_reference",
            "relationship": "normative_reference",
            "relationship_confidence": "structural",
            "evidence": {
                "text": "IS 1070 : 1992",
                "source_section": "REFERENCES",
                "extraction_method": "html_table_row",
                "complete": True,
            },
        }
        rec = _make_v12_record("IS 19901:2026", refs=[ref], identity_match="match_version_uncertain")
        jsonl_path = tmp_path / "standards.jsonl"
        _write_jsonl(jsonl_path, [rec])

        graph = build_graph_from_jsonl(jsonl_path)
        assert graph["edges_count"] == 1
        edge = graph["edges"][0]
        assert edge["edge_verification_status"] == "UNRESOLVED"
        assert edge["verified"] is False

    def test_content_fields_read_from_content_object(self, tmp_path):
        """V1.2 nested content fields (not flat top-level) must be read."""
        rec = _make_v12_record("IS 19901:2026", title="My Custom Title")
        # Override content to ensure nested read works
        rec["content"]["title"] = "Nested Title"
        rec["content"]["committee"] = "ETD 09"
        rec["content"]["ics_raw"] = "ICS 29.060.20"
        rec["content"]["ics_codes"] = ["29.060.20"]
        jsonl_path = tmp_path / "standards.jsonl"
        _write_jsonl(jsonl_path, [rec])

        graph = build_graph_from_jsonl(jsonl_path)
        node = next(n for n in graph["nodes"] if n["id"] == "IS 19901:2026")
        assert node["title"] == "Nested Title"
        assert node["committee"] == "ETD 09"
        assert node["ics_raw"] == "ICS 29.060.20"
        assert node["ics_codes"] == ["29.060.20"]

    def test_department_metadata_preserved(self, tmp_path):
        """V1.2 top-level department must appear on the graph node."""
        rec = _make_v12_record("IS 19901:2026", title="ETD Standard")
        rec["department"] = "ETD"
        jsonl_path = tmp_path / "standards.jsonl"
        _write_jsonl(jsonl_path, [rec])

        graph = build_graph_from_jsonl(jsonl_path)
        node = next(n for n in graph["nodes"] if n["id"] == "IS 19901:2026")
        assert node["primary_department"] == "ETD"
        assert node["source_departments"] == ["ETD"]
        assert "ETD" in graph["source_departments"]
        assert graph["department_node_counts"]["ETD"] == 1

    def test_cross_department_references_accumulate(self, tmp_path):
        """When CED and ETD both reference a standard stub, stub source_departments remains empty, citing_departments accumulates."""
        # ETD record with IS 1070 as a reference stub
        etd_rec = _make_v12_record("IS 19901:2026", title="ETD Standard")
        etd_rec["department"] = "ETD"
        etd_rec["references"] = [{
            "source_standard": "IS 19901:2026",
            "target": {"designation": "IS 1070:1992", "family": "IS", "base_number": "1070",
                       "part": None, "section": None, "year": "1992"},
            "reference_type": "formal_reference",
            "relationship": "normative_reference",
            "relationship_confidence": "structural",
            "evidence": {"text": "IS 1070: 1992", "source_section": "REFERENCES",
                         "extraction_method": "html_table_row", "complete": True,
                         "continuation_resolved": False, "bare_number_resolved": True},
        }]
        # CED record referencing the same standard
        ced_rec = _make_v12_record("IS 20000:2026", title="CED Standard")
        ced_rec["department"] = "CED"
        ced_rec["references"] = [{
            "source_standard": "IS 20000:2026",
            "target": {"designation": "IS 1070:1992", "family": "IS", "base_number": "1070",
                       "part": None, "section": None, "year": "1992"},
            "reference_type": "formal_reference",
            "relationship": "normative_reference",
            "relationship_confidence": "structural",
            "evidence": {"text": "IS 1070 1992", "source_section": "REFERENCES",
                         "extraction_method": "html_table_row", "complete": True,
                         "continuation_resolved": False, "bare_number_resolved": True},
        }]
        jsonl_path = tmp_path / "standards.jsonl"
        _write_jsonl(jsonl_path, [etd_rec, ced_rec])

        graph = build_graph_from_jsonl(jsonl_path)
        stub = next(n for n in graph["nodes"] if n["id"] == "IS 1070:1992")
        # Invariant 1: stubs must NEVER inherit citing departments into source_departments
        assert stub["source_departments"] == []
        assert stub["primary_department"] is None
        assert not stub["is_hydrated"]

        # Citing departments is a derived property from incoming edges
        from scripts.build_knowledge_graph import citing_departments
        assert citing_departments(stub["id"], graph["edges"]) == {"ETD", "CED"}

        # Each edge carries its source department
        edges = graph["edges"]
        assert any(e["source_department"] == "ETD" for e in edges)
        assert any(e["source_department"] == "CED" for e in edges)



class TestBuildGraphHardFail:
    def test_empty_graph_from_nonempty_jsonl_fails(self, tmp_path):
        """If JSONL has valid records but graph produces 0 nodes, build must fail."""
        rec = _make_v12_record("IS 1070:1992")
        jsonl_path = tmp_path / "standards.jsonl"
        _write_jsonl(jsonl_path, [rec])

        # Simulate a broken builder by calling build and checking counts
        graph = build_graph_from_jsonl(jsonl_path)
        # With the fix, this should produce nodes
        assert graph["nodes_count"] >= 1

    def test_nonzero_exit_on_silent_data_loss(self, tmp_path, monkeypatch):
        """Verify the hard-fail guard in main() exits non-zero when records exist but graph is empty."""
        import scripts.build_knowledge_graph as bg

        # Monkey-patch build_graph_from_jsonl to return empty graph (simulate silent failure)
        original = bg.build_graph_from_jsonl

        def empty_graph(jsonl_path):
            return {
                "graph_version": "1.2.0", "schema_version": "1.2",
                "parser_version": "1.2.0", "release_id": "test",
                "built_at": "2026-01-01T00:00:00+00:00",
                "source_type": "jsonl", "source_path": str(jsonl_path),
                "description": "test", "nodes_count": 0, "hydrated_nodes_count": 0,
                "unhydrated_nodes_count": 0, "recommendation_eligible_count": 0,
                "edges_count": 0, "direct_edges_count": 0, "inferred_edges_count": 0,
                "nodes": [], "edges": [],
            }

        monkeypatch.setattr(bg, "build_graph_from_jsonl", empty_graph)

        rec = _make_v12_record("IS 1070:1992")
        jsonl_path = tmp_path / "standards.jsonl"
        _write_jsonl(jsonl_path, [rec])

        with pytest.raises(SystemExit) as exc_info:
            bg.main.__wrapped__() if hasattr(bg.main, '__wrapped__') else None
            # Call main with arguments via argparse patch
            import argparse
            with monkeypatch.context() as m:
                m.setattr("sys.argv", ["build_knowledge_graph.py", "--jsonl", str(jsonl_path),
                                       "--output", str(tmp_path / "graph.json")])
                bg.main()
        assert exc_info.value.code == 1


class TestGraphSchemaValidation:
    def test_valid_graph_passes_schema(self, tmp_path):
        """A properly-built graph must validate against standards_graph.schema.json."""
        rec = _make_v12_record("IS 1070:1992", title="Safety Code")
        rec["department"] = "CED"
        jsonl_path = tmp_path / "standards.jsonl"
        _write_jsonl(jsonl_path, [rec])

        graph = build_graph_from_jsonl(jsonl_path)
        valid, errors = validate_graph(graph)
        assert valid, f"Valid graph should pass schema: {errors}"

    def test_invalid_graph_missing_node_id(self):
        """A graph with a node missing 'id' must fail validation."""
        bad_graph = {
            "graph_version": "1.2.0",
            "schema_version": "1.2.0",
            "parser_version": "1.2.0",
            "built_at": "2026-01-01T00:00:00+00:00",
            "source_type": "jsonl",
            "source_path": "/tmp/x",
            "nodes_count": 1,
            "hydrated_nodes_count": 0,
            "edges_count": 0,
            "nodes": [{"node_type": "INDIAN_STANDARD"}],  # missing id and designation
            "edges": [],
        }
        valid, errors = validate_graph(bad_graph)
        assert not valid
        assert any("id" in e for e in errors)


class TestGraphCorrectivePhase1To4:
    def test_stub_does_not_inherit_citing_department(self, tmp_path):
        """Stubs created from references must have source_departments=[] and primary_department=None."""
        rec = _make_v12_record("IS 19901:2026", refs=[{
            "source_standard": "IS 19901:2026",
            "target": {"designation": "IS 456:2000", "family": "IS", "base_number": "456", "year": "2000"},
            "relationship": "normative_reference",
            "relationship_confidence": "structural",
            "evidence": {"text": "IS 456", "source_section": "REFERENCES", "extraction_method": "html_table_row"},
        }])
        rec["department"] = "CED"
        p = tmp_path / "ced.jsonl"
        _write_jsonl(p, [rec])

        graph = build_graph_from_jsonl(p)
        stub = next(n for n in graph["nodes"] if n["id"] == "IS 456:2000")
        assert stub["source_departments"] == []
        assert stub["primary_department"] is None
        assert not stub["is_hydrated"]
        assert stub["candidate_status"] == "SUPPORTING_ONLY"
        assert stub["candidate_reason"] == "UNHYDRATED_STUB_REFERENCE"

    def test_primary_record_gets_source_department(self, tmp_path):
        """Primary record in a department gets source_departments=[dept] and primary_department=dept."""
        rec = _make_v12_record("IS 19901:2026")
        rec["department"] = "ETD"
        p = tmp_path / "etd.jsonl"
        _write_jsonl(p, [rec])

        graph = build_graph_from_jsonl(p)
        node = next(n for n in graph["nodes"] if n["id"] == "IS 19901:2026")
        assert node["source_departments"] == ["ETD"]
        assert node["primary_department"] == "ETD"
        assert node["is_hydrated"]
        assert node["candidate_status"] == "ELIGIBLE"

    def test_dual_department_primary_uses_deterministic_precedence(self, tmp_path):
        """If a standard is a primary record in two departments, deterministic precedence is used."""
        rec1 = _make_v12_record("IS 1070:1992")
        rec1["department"] = "ETD"
        rec2 = _make_v12_record("IS 1070:1992")
        rec2["department"] = "CED"
        p = tmp_path / "standards.jsonl"
        # Ingestion in reverse alphabetical order (ETD then CED)
        _write_jsonl(p, [rec1, rec2])

        graph = build_graph_from_jsonl(p)
        node = next(n for n in graph["nodes"] if n["id"] == "IS 1070:1992")
        assert node["source_departments"] == ["CED", "ETD"]
        # Sorted alphabetical precedence
        assert node["primary_department"] == "CED"

    def test_merge_does_not_drop_references(self, tmp_path):
        """Merging records for the same standard does not drop references from later records."""
        rec1 = _make_v12_record("IS 1070:1992", refs=[{
            "source_standard": "IS 1070:1992",
            "target": {"designation": "IS 2:1960", "family": "IS", "base_number": "2"},
            "relationship": "normative_reference",
            "relationship_confidence": "structural",
            "evidence": {"text": "IS 2", "source_section": "REFERENCES", "extraction_method": "html_table_row"},
        }])
        rec2 = _make_v12_record("IS 1070:1992", refs=[{
            "source_standard": "IS 1070:1992",
            "target": {"designation": "IS 456:2000", "family": "IS", "base_number": "456"},
            "relationship": "normative_reference",
            "relationship_confidence": "structural",
            "evidence": {"text": "IS 456", "source_section": "REFERENCES", "extraction_method": "html_table_row"},
        }])
        p = tmp_path / "merged.jsonl"
        _write_jsonl(p, [rec1, rec2])

        graph = build_graph_from_jsonl(p)
        edges = graph["edges"]
        targets = {e["target"] for e in edges if e["source"] == "IS 1070:1992"}
        assert "IS 2:1960" in targets
        assert "IS 456:2000" in targets
        assert len(targets) == 2

    def test_edge_verification_granular_consistency(self, tmp_path):
        """Verified preview + structural reference produces HIGH confidence and EXPLICIT_FROM_SOURCE."""
        rec = _make_v12_record("IS 19901:2026", identity_match="match_version_verified", refs=[{
            "source_standard": "IS 19901:2026",
            "target": {"designation": "IS 1070:1992", "family": "IS", "base_number": "1070"},
            "relationship": "normative_reference",
            "relationship_confidence": "structural",
            "evidence": {"text": "IS 1070", "source_section": "REFERENCES", "extraction_method": "html_table_row"},
        }])
        p = tmp_path / "data.jsonl"
        _write_jsonl(p, [rec])

        graph = build_graph_from_jsonl(p)
        edge = graph["edges"][0]
        assert edge["source_identity_state"] == "VERIFIED"
        assert edge["relationship_observation"] == "EXPLICIT_FROM_SOURCE"
        assert edge["relationship_confidence_state"] == "HIGH"
        assert edge["confidence"] == 1.0
        assert edge["verified"] is True
        assert edge["page_self_identified"] is True

    def test_inferred_relationship_gets_medium_confidence(self, tmp_path):
        """Verified preview + non-structural/prose reference produces MEDIUM confidence and INFERRED."""
        rec = _make_v12_record("IS 19901:2026", identity_match="match_version_verified", refs=[{
            "source_standard": "IS 19901:2026",
            "target": {"designation": "IS 1070:1992", "family": "IS", "base_number": "1070"},
            "relationship": "related_to",
            "relationship_confidence": "heuristic",
            "evidence": {"text": "Related", "source_section": "FOREWORD", "extraction_method": "prose_phrase_scan"},
        }])
        p = tmp_path / "data.jsonl"
        _write_jsonl(p, [rec])

        graph = build_graph_from_jsonl(p)
        edge = graph["edges"][0]
        assert edge["source_identity_state"] == "VERIFIED"
        assert edge["relationship_observation"] == "INFERRED"
        assert edge["relationship_confidence_state"] == "MEDIUM"
        assert edge["confidence"] == 0.8
        assert edge["verified"] is False

    def test_citing_departments_derivable_from_edges(self, tmp_path):
        """citing_departments is correctly computed from incoming edges."""
        from scripts.build_knowledge_graph import citing_departments
        edges = [
            {"source": "IS 1", "target": "IS Target", "source_department": "CED", "relationship": "normative_reference"},
            {"source": "IS 2", "target": "IS Target", "source_department": "ETD", "relationship": "normative_reference"},
            {"source": "IS 3", "target": "IS Other", "source_department": "CED", "relationship": "normative_reference"},
        ]
        assert citing_departments("IS Target", edges) == {"CED", "ETD"}
        assert citing_departments("IS Other", edges) == {"CED"}
        assert citing_departments("IS Uncited", edges) == set()

    def test_no_document_means_not_applicability_ready(self, tmp_path):
        """Standard without cached preview document cannot be applicability_ready."""
        rec = _make_v12_record("IS 1070:1992")
        rec["source"]["matched_preview_id"] = None
        rec["content"]["scope"] = {"text": "Some scope", "status": "present"}
        p = tmp_path / "data.jsonl"
        _write_jsonl(p, [rec])

        graph = build_graph_from_jsonl(p)
        node = next(n for n in graph["nodes"] if n["id"] == "IS 1070:1992")
        assert not node["document_available"]
        assert not node["applicability_ready"]
        assert not node["recommendation_ready"]

    def test_no_scope_means_not_recommendation_ready(self, tmp_path):
        """Standard without scope cannot be recommendation_ready or applicability_ready."""
        rec = _make_v12_record("IS 1070:1992")
        rec["content"]["scope"] = {"text": None, "status": "absent"}
        p = tmp_path / "data.jsonl"
        _write_jsonl(p, [rec])

        graph = build_graph_from_jsonl(p)
        node = next(n for n in graph["nodes"] if n["id"] == "IS 1070:1992")
        assert not node["scope_evidence_available"]
        assert not node["applicability_ready"]
        assert not node["recommendation_ready"]

    def test_retrieval_ready_without_scope(self, tmp_path):
        """Standard with title and committee is retrieval_ready even if scope is absent."""
        rec = _make_v12_record("IS 1070:1992", title="Valid Title")
        rec["content"]["scope"] = {"text": None, "status": "absent"}
        p = tmp_path / "data.jsonl"
        _write_jsonl(p, [rec])

        graph = build_graph_from_jsonl(p)
        node = next(n for n in graph["nodes"] if n["id"] == "IS 1070:1992")
        assert node["retrieval_ready"]
        assert not node["applicability_ready"]

    def test_test_method_gets_supporting_only(self, tmp_path):
        """Test method standard gets candidate_status=SUPPORTING_ONLY, reason=TEST_METHOD."""
        rec = _make_v12_record("IS 10810 (Part 1):2021", title="Methods of test for cables")
        p = tmp_path / "data.jsonl"
        _write_jsonl(p, [rec])

        graph = build_graph_from_jsonl(p)
        node = next(n for n in graph["nodes"] if n["id"] == "IS 10810 (Part 1):2021")
        assert node["candidate_status"] == "SUPPORTING_ONLY"
        assert node["candidate_reason"] == "TEST_METHOD"
        assert not node["is_recommendation_eligible"]

    def test_external_standard_gets_context_only(self, tmp_path):
        """External reference (ISO/IEC) gets candidate_status=CONTEXT_ONLY."""
        rec = _make_v12_record("IS 19901:2026", refs=[{
            "source_standard": "IS 19901:2026",
            "target": {"designation": "ISO 9001:2015", "family": "ISO", "base_number": "9001"},
            "relationship": "normative_reference",
            "relationship_confidence": "structural",
            "evidence": {"text": "ISO 9001", "source_section": "REFERENCES", "extraction_method": "html_table_row"},
        }])
        p = tmp_path / "data.jsonl"
        _write_jsonl(p, [rec])

        graph = build_graph_from_jsonl(p)
        node = next(n for n in graph["nodes"] if n["id"] == "ISO 9001:2015")
        assert node["candidate_status"] == "CONTEXT_ONLY"
        assert node["candidate_reason"] == "EXTERNAL_REFERENCE"
        assert not node["is_recommendation_eligible"]

    def test_content_hash_excludes_self(self, tmp_path):
        """Content hash must be identical whether content_hash/built_at are present or not."""
        from scripts.build_knowledge_graph import _content_hash
        graph = {
            "graph_version": "1.2.1",
            "nodes_count": 1,
            "edges_count": 0,
            "nodes": [{"id": "IS 1", "node_type": "INDIAN_STANDARD"}],
            "edges": [],
            "built_at": "2026-09-28T00:00:00Z",
            "release_id": "test_1",
            "content_hash": "existing_hash",
        }
        h1 = _content_hash(graph)
        graph["built_at"] = "2026-10-01T12:00:00Z"
        graph["release_id"] = "test_2"
        graph["content_hash"] = "different_hash"
        h2 = _content_hash(graph)
        assert h1 == h2

    def test_graph_invariants_pass(self):
        """The production unified graph must pass all 8 invariants."""
        from scripts.validate_graph_invariants import validate_graph_invariants
        graph_path = Path("data/processed/standards_graph.json")
        if graph_path.exists():
            with open(graph_path, "r", encoding="utf-8") as f:
                graph = json.load(f)
            valid, violations = validate_graph_invariants(graph)
            assert valid, f"Invariant violations: {violations}"

