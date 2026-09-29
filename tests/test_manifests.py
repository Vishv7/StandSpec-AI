"""
Tests for the dataset manifest generator (src/manifest.py).

Verifies that manifests contain reproducible hashes, row counts,
version metadata, and graph statistics.

Tests are 100% network-independent (A15).
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.manifest import (
    generate_department_manifest,
    generate_release_manifest,
    write_manifest,
    _sha256,
    _count_jsonl,
)


def _write_jsonl(path: Path, records: list):
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def test_sha256_reproducible(tmp_path):
    """SHA256 of the same file content must be stable."""
    f1 = tmp_path / "a.jsonl"
    f1.write_text(json.dumps({"x": 1}) + "\n")
    f2 = tmp_path / "b.jsonl"
    f2.write_text(json.dumps({"x": 1}) + "\n", encoding="utf-8")
    assert _sha256(f1) == _sha256(f2)


def test_count_jsonl(tmp_path):
    """_count_jsonl must skip blank lines and comments."""
    f = tmp_path / "data.jsonl"
    f.write_text(json.dumps({"a": 1}) + "\n" + "\n" + "# comment\n" + json.dumps({"b": 2}) + "\n")
    assert _count_jsonl(f) == 2


def test_department_manifest_structure(tmp_path):
    """generate_department_manifest must produce required fields."""
    input_file = tmp_path / "input.csv"
    input_file.write_text("dummy")
    standards_jsonl = tmp_path / "ETD_standards.jsonl"
    _write_jsonl(standards_jsonl, [{"designation": "IS 1070:1992"}])

    manifest = generate_department_manifest(
        department="ETD",
        input_file=input_file,
        standards_jsonl=standards_jsonl,
        references_jsonl=tmp_path / "nonexistent.jsonl",
        availability_jsonl=tmp_path / "nonexistent.jsonl",
        availability_csv=tmp_path / "nonexistent.csv",
        enriched_xlsx=tmp_path / "nonexistent.xlsx",
        collection_report=tmp_path / "nonexistent.json",
    )

    assert manifest["department"] == "ETD"
    assert "format_version" in manifest
    assert "build_timestamp" in manifest
    assert "input_sha256" in manifest
    assert "versions" in manifest
    assert manifest["versions"]["schema_version"] in ("1.2", "2.0")
    assert "outputs" in manifest
    assert "standards_jsonl" in manifest["outputs"]
    assert manifest["outputs"]["standards_jsonl"]["record_count"] == 1
    # Referenced jsonl files that don't exist should not appear
    assert "references_jsonl" not in manifest["outputs"]


def test_release_manifest_combines_departments(tmp_path):
    """generate_release_manifest must aggregate department manifests and graph stats."""
    (tmp_path / "input.xlsx").write_text("dummy")

    graph = {
        "graph_version": "1.2.0",
        "schema_version": "1.2.0",
        "nodes_count": 2,
        "hydrated_nodes_count": 1,
        "unhydrated_nodes_count": 1,
        "edges_count": 1,
        "recommendation_eligible_count": 1,
        "source_departments": ["CED", "ETD"],
        "department_node_counts": {"CED": 1, "ETD": 1},
        "department_hydrated_counts": {"CED": 1, "ETD": 0},
        "nodes": [],
        "edges": [],
    }
    graph_path = tmp_path / "graph.json"
    with open(graph_path, "w") as f:
        json.dump(graph, f)

    dep_manifest = generate_department_manifest(
        department="CED",
        input_file=tmp_path / "input.xlsx",
        standards_jsonl=tmp_path / "nonexistent.jsonl",
        references_jsonl=tmp_path / "nonexistent.jsonl",
        availability_jsonl=tmp_path / "nonexistent.jsonl",
        availability_csv=tmp_path / "nonexistent.csv",
        enriched_xlsx=tmp_path / "nonexistent.xlsx",
        collection_report=tmp_path / "nonexistent.json",
    )

    release = generate_release_manifest(
        release_id="standspec_prototype_v1",
        department_manifests=[dep_manifest],
        graph_path=graph_path,
    )

    assert release["release_id"] == "standspec_prototype_v1"
    assert release["departments"][0]["department"] == "CED"
    assert release["graph"]["sha256"] is not None
    assert release["graph"]["nodes_count"] == 2
    assert release["graph"]["source_departments"] == ["CED", "ETD"]


def test_write_manifest_returns_hash(tmp_path):
    """write_manifest must write JSON and return a sha256."""
    manifest = {"department": "ETD", "format_version": "1.0"}
    path = tmp_path / "manifests" / "ETD_manifest.json"
    h = write_manifest(manifest, path)

    assert path.exists()
    assert len(h) == 64
    with open(path) as f:
        loaded = json.load(f)
    assert loaded["department"] == "ETD"
