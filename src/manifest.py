"""
Dataset manifest generator for StandSpec AI.

Generates reproducible release manifests with input/output hashes,
row counts, version metadata, and per-department statistics.

Manifest schema follows docs/reviews/6th_audit_manifest_contract.md.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import __version__, PARSER_VERSION
from src.version import COLLECTOR_SCHEMA_VERSION as SCHEMA_VERSION


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _count_jsonl(path: Path) -> int:
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.strip().startswith("#"):
                count += 1
    return count


def _count_xlsx_input_rows(path: Path) -> dict:
    """Count input rows using the same ingestion logic as excel_reader.py."""
    try:
        from src.excel_reader import read_excel, _find_column_index, COLUMN_ALIASES
        headers, rows, _, _ = read_excel(path)
        std_idx = _find_column_index(headers, COLUMN_ALIASES["standard_number"])
        designations = [
            str(r[std_idx]).strip()
            for r in rows
            if std_idx is not None and std_idx < len(r) and r[std_idx]
        ]
        return {
            "total_rows": len(rows),
            "unique_designations": len(set(designations)),
            "duplicate_designations": len(rows) - len(set(designations)),
        }
    except Exception as e:
        return {
            "total_rows": 0,
            "unique_designations": 0,
            "duplicate_designations": 0,
            "error": str(e),
        }



def _content_hash(graph: dict) -> str:
    """
    Hash graph content excluding ALL nondeterministic and self-referential fields.
    """
    EXCLUDED_FIELDS = {"built_at", "release_id", "content_hash"}
    content = {k: v for k, v in graph.items() if k not in EXCLUDED_FIELDS}
    if "nodes" in content and isinstance(content["nodes"], list):
        content["nodes"] = sorted(content["nodes"], key=lambda n: n.get("id", ""))
    if "edges" in content and isinstance(content["edges"], list):
        content["edges"] = sorted(
            content["edges"],
            key=lambda e: (e.get("source", ""), e.get("target", ""), e.get("relationship", ""))
        )
    canonical = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def generate_department_manifest(
    department: str,
    input_file: Path,
    standards_jsonl: Path,
    references_jsonl: Path,
    availability_jsonl: Path,
    availability_csv: Path,
    enriched_xlsx: Path,
    collection_report: Path,
    output_graph: Path = None,
) -> dict:
    """
    Generate a department-level manifest with reproducible hashes and statistics.
    """
    from src.collector import _get_git_commit_metadata

    git_commit, commit_source = _get_git_commit_metadata()

    input_p = Path(input_file)
    input_rows = 0
    input_row_details = None
    if input_p.exists():
        if input_p.suffix == ".xlsx":
            input_row_details = _count_xlsx_input_rows(input_p)
            input_rows = input_row_details["total_rows"]
        elif input_p.suffix == ".jsonl":
            input_rows = _count_jsonl(input_p)
        input_hash = _sha256(input_p)
    else:
        input_hash = "NONEXISTENT"

    manifest = {
        "department": department.upper(),
        "format_version": "1.0",
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "versions": {
            "collector_version": __version__,
            "parser_version": PARSER_VERSION,
            "schema_version": SCHEMA_VERSION,
            "code_commit": git_commit,
            "code_version_source": commit_source,
        },
        "input_file": str(input_file),
        "input_sha256": input_hash,
        "input_rows": input_rows,
        "outputs": {},
    }

    if input_row_details:
        manifest["input_row_details"] = input_row_details

    output_files = {
        "standards_jsonl": standards_jsonl,
        "references_jsonl": references_jsonl,
        "availability_jsonl": availability_jsonl,
        "availability_csv": availability_csv,
        "enriched_xlsx": enriched_xlsx,
        "collection_report": collection_report,
        "graph": output_graph,
    }

    for name, path in output_files.items():
        if path and Path(path).exists():
            p = Path(path)
            try:
                file_hash = _sha256(p)
            except PermissionError:
                file_hash = "LOCKED_FILE_SKIPPED"
            entry = {
                "path": str(p),
                "sha256": file_hash,
            }
            if p.suffix == ".jsonl":
                entry["record_count"] = _count_jsonl(p)
            manifest["outputs"][name] = entry

    # Collect per-department graph stats if graph available
    if output_graph and Path(output_graph).exists():
        with open(output_graph, "r", encoding="utf-8") as f:
            graph = json.load(f)
        manifest["graph_stats"] = {
            "nodes_count": graph.get("nodes_count"),
            "hydrated_nodes_count": graph.get("hydrated_nodes_count"),
            "edges_count": graph.get("edges_count"),
            "department_node_count": graph.get("department_node_counts", {}).get(department.upper(), 0),
            "department_hydrated_count": graph.get("department_hydrated_counts", {}).get(department.upper(), 0),
        }

    return manifest


def generate_release_manifest(
    release_id: str,
    department_manifests: list[dict],
    graph_path: Path,
) -> dict:
    """
    Generate a combined multi-department release manifest.
    """
    graph_p = Path(graph_path)
    graph_hash = _sha256(graph_p) if graph_p.exists() else None
    graph_content_hash = None

    if graph_p.exists():
        with open(graph_p, "r", encoding="utf-8") as f:
            graph = json.load(f)
        graph_content_hash = _content_hash(graph)
    else:
        graph = {}

    return {
        "release_id": release_id,
        "format_version": "1.0",
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "versions": {
            "collector_version": __version__,
            "parser_version": PARSER_VERSION,
            "schema_version": SCHEMA_VERSION,
        },
        "departments": [m for m in department_manifests if m],
        "graph": {
            "path": str(graph_path),
            "sha256": graph_hash,
            "content_hash": graph_content_hash,
            "nodes_count": graph.get("nodes_count"),
            "hydrated_nodes_count": graph.get("hydrated_nodes_count"),
            "unhydrated_nodes_count": graph.get("unhydrated_nodes_count"),
            "edges_count": graph.get("edges_count"),
            "recommendation_eligible_count": graph.get("recommendation_eligible_count"),
            "source_departments": graph.get("source_departments", []),
            "department_node_counts": graph.get("department_node_counts", {}),
            "department_hydrated_counts": graph.get("department_hydrated_counts", {}),
        },
    }


def write_manifest(manifest: dict, path: Path) -> str:
    """Write manifest to disk and return its sha256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return _sha256(path)
