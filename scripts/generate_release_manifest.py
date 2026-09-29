"""
Authoritative Single Release Manifest Generator and Validator — StandSpec AI
Generates portable, reproducible release manifests and validates manifest integrity.

Pipeline:
  src/version.py -> scripts/generate_release_manifest.py -> authoritative manifest -> integrity validator

Usage:
  python scripts/generate_release_manifest.py          # Generate/Update authoritative manifests
  python scripts/generate_release_manifest.py --check  # Verify manifest integrity without modifying
"""

import sys
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.version import (
    __version__,
    ENGINE_VERSION,
    RELEASE_ID,
    FORMAT_VERSION,
    SCHEMA_VERSION,
    COLLECTOR_VERSION,
    PARSER_VERSION,
    PYTHON_RUNTIME,
    PYTEST_VERSION,
)


def compute_sha256(filepath: Path) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def count_lines(filepath: Path) -> int:
    """Counts non-empty, non-comment lines in a file."""
    if not filepath.exists():
        return 0
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for line in f if line.strip() and not line.strip().startswith("#"))


def generate_manifest_data() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Build the unified release manifest and department manifests from disk."""
    graph_path = PROJECT_ROOT / "data" / "processed" / "standards_graph.json"
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    ced_nodes = [n for n in nodes if "CED" in (n.get("source_departments") or []) or n.get("primary_department") == "CED"]
    etd_nodes = [n for n in nodes if "ETD" in (n.get("source_departments") or []) or n.get("primary_department") == "ETD"]
    ced_hydrated = sum(1 for n in ced_nodes if n.get("is_hydrated"))
    etd_hydrated = sum(1 for n in etd_nodes if n.get("is_hydrated"))

    # File paths
    ced_xlsx = PROJECT_ROOT / "data" / "input" / "Civil Engineering Department (CED).xlsx"
    ced_standards = PROJECT_ROOT / "data" / "processed" / "CED" / "CED_standards.jsonl"
    ced_references = PROJECT_ROOT / "data" / "processed" / "CED" / "CED_references.jsonl"
    ced_avail = PROJECT_ROOT / "data" / "processed" / "CED" / "CED_source_availability.jsonl"

    etd_xlsx = PROJECT_ROOT / "data" / "input" / "Electrotechnical Department (ETD).xlsx"
    etd_standards = PROJECT_ROOT / "data" / "processed" / "ETD" / "ETD_standards.jsonl"
    etd_references = PROJECT_ROOT / "data" / "processed" / "ETD" / "ETD_references.jsonl"
    etd_avail = PROJECT_ROOT / "data" / "processed" / "ETD" / "ETD_source_availability.jsonl"

    test_benchmark = PROJECT_ROOT / "data" / "benchmarks" / "test.jsonl"
    val_benchmark = PROJECT_ROOT / "data" / "benchmarks" / "val.jsonl"
    train_benchmark = PROJECT_ROOT / "data" / "benchmarks" / "train.jsonl"
    adversarial_benchmark = PROJECT_ROOT / "data" / "benchmarks" / "adversarial.jsonl"
    challenge_benchmark = PROJECT_ROOT / "data" / "benchmarks" / "challenge.jsonl"
    coverage_boundary_benchmark = PROJECT_ROOT / "data" / "benchmarks" / "coverage_boundary.jsonl"
    open_world_benchmark = PROJECT_ROOT / "data" / "benchmarks" / "open_world.jsonl"

    calibrator_file = PROJECT_ROOT / "data" / "models" / "calibrator_v1.json"

    qco_file = PROJECT_ROOT / "data" / "regulatory" / "qco_orders.jsonl"
    crs_file = PROJECT_ROOT / "data" / "regulatory" / "crs_rules.jsonl"
    src_manifest = PROJECT_ROOT / "data" / "regulatory" / "source_manifest.json"

    ced_dept = {
        "department": "CED",
        "input_file": "data/input/Civil Engineering Department (CED).xlsx",
        "input_sha256": compute_sha256(ced_xlsx) if ced_xlsx.exists() else None,
        "input_rows": 1935,
        "outputs": {
            "standards_jsonl": {
                "path": "data/processed/CED/CED_standards.jsonl",
                "sha256": compute_sha256(ced_standards) if ced_standards.exists() else None,
                "record_count": count_lines(ced_standards),
            },
            "references_jsonl": {
                "path": "data/processed/CED/CED_references.jsonl",
                "sha256": compute_sha256(ced_references) if ced_references.exists() else None,
                "record_count": count_lines(ced_references),
            },
            "availability_jsonl": {
                "path": "data/processed/CED/CED_source_availability.jsonl",
                "sha256": compute_sha256(ced_avail) if ced_avail.exists() else None,
                "record_count": count_lines(ced_avail),
            },
        },
    }

    etd_dept = {
        "department": "ETD",
        "input_file": "data/input/Electrotechnical Department (ETD).xlsx",
        "input_sha256": compute_sha256(etd_xlsx) if etd_xlsx.exists() else None,
        "input_rows": 1944,
        "outputs": {
            "standards_jsonl": {
                "path": "data/processed/ETD/ETD_standards.jsonl",
                "sha256": compute_sha256(etd_standards) if etd_standards.exists() else None,
                "record_count": count_lines(etd_standards),
            },
            "references_jsonl": {
                "path": "data/processed/ETD/ETD_references.jsonl",
                "sha256": compute_sha256(etd_references) if etd_references.exists() else None,
                "record_count": count_lines(etd_references),
            },
            "availability_jsonl": {
                "path": "data/processed/ETD/ETD_source_availability.jsonl",
                "sha256": compute_sha256(etd_avail) if etd_avail.exists() else None,
                "record_count": count_lines(etd_avail),
            },
        },
    }

    test_eval_p = PROJECT_ROOT / "data" / "evaluations" / "test_evaluation.json"
    val_eval_p = PROJECT_ROOT / "data" / "evaluations" / "val_evaluation.json"
    open_world_eval_p = PROJECT_ROOT / "data" / "evaluations" / "open_world_evaluation.json"
    adv_eval_p = PROJECT_ROOT / "data" / "evaluations" / "adversarial_evaluation.json"
    chall_eval_p = PROJECT_ROOT / "data" / "evaluations" / "challenge_evaluation.json"
    cov_eval_p = PROJECT_ROOT / "data" / "evaluations" / "coverage_boundary_evaluation.json"

    # Compute evaluation artifacts if not present
    if not test_eval_p.exists():
        from scripts.evaluate_recommendation import evaluate_engine_on_benchmark
        test_eval_p.parent.mkdir(parents=True, exist_ok=True)
        report = evaluate_engine_on_benchmark(test_benchmark, graph_path, top_k=5)
        payload = {
            "benchmark_path": str(test_benchmark.as_posix()),
            "graph_path": str(graph_path.as_posix()),
            "top_k": 5,
            "metrics": {k: v for k, v in report.items() if k != "per_query_results"},
            "per_query_results": report.get("per_query_results", []),
        }
        with open(test_eval_p, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    with open(test_eval_p, "r", encoding="utf-8") as f:
        test_eval_data = json.load(f)
    test_metrics = test_eval_data.get("metrics", {})

    release_manifest = {
        "release_id": RELEASE_ID,
        "format_version": FORMAT_VERSION,
        "build_timestamp": "2026-09-28T17:35:46+00:00",
        "versions": {
            "engine_version": ENGINE_VERSION,
            "collector_version": COLLECTOR_VERSION,
            "parser_version": PARSER_VERSION,
            "schema_version": SCHEMA_VERSION,
            "python_runtime": PYTHON_RUNTIME,
            "pytest_version": PYTEST_VERSION,
        },
        "artifacts": {
            "knowledge_graph": {
                "path": "data/processed/standards_graph.json",
                "sha256": compute_sha256(graph_path),
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "ced_hydrated": ced_hydrated,
                "etd_hydrated": etd_hydrated,
            },
            "benchmarks": {
                "test": {
                    "path": "data/benchmarks/test.jsonl",
                    "sha256": compute_sha256(test_benchmark),
                    "record_count": count_lines(test_benchmark),
                },
                "val": {
                    "path": "data/benchmarks/val.jsonl",
                    "sha256": compute_sha256(val_benchmark),
                    "record_count": count_lines(val_benchmark),
                },
                "train": {
                    "path": "data/benchmarks/train.jsonl",
                    "sha256": compute_sha256(train_benchmark),
                    "record_count": count_lines(train_benchmark),
                },
                "adversarial": {
                    "path": "data/benchmarks/adversarial.jsonl",
                    "sha256": compute_sha256(adversarial_benchmark),
                    "record_count": count_lines(adversarial_benchmark),
                },
                "challenge": {
                    "path": "data/benchmarks/challenge.jsonl",
                    "sha256": compute_sha256(challenge_benchmark),
                    "record_count": count_lines(challenge_benchmark),
                },
                "coverage_boundary": {
                    "path": "data/benchmarks/coverage_boundary.jsonl",
                    "sha256": compute_sha256(coverage_boundary_benchmark),
                    "record_count": count_lines(coverage_boundary_benchmark),
                },
                "open_world": {
                    "path": "data/benchmarks/open_world.jsonl",
                    "sha256": compute_sha256(open_world_benchmark),
                    "record_count": count_lines(open_world_benchmark),
                },
            },
            "evaluation_artifacts": {
                "test": {
                    "path": "data/evaluations/test_evaluation.json",
                    "sha256": compute_sha256(test_eval_p),
                },
                "val": {
                    "path": "data/evaluations/val_evaluation.json",
                    "sha256": compute_sha256(val_eval_p) if val_eval_p.exists() else None,
                },
                "open_world": {
                    "path": "data/evaluations/open_world_evaluation.json",
                    "sha256": compute_sha256(open_world_eval_p) if open_world_eval_p.exists() else None,
                },
                "adversarial": {
                    "path": "data/evaluations/adversarial_evaluation.json",
                    "sha256": compute_sha256(adv_eval_p) if adv_eval_p.exists() else None,
                },
                "challenge": {
                    "path": "data/evaluations/challenge_evaluation.json",
                    "sha256": compute_sha256(chall_eval_p) if chall_eval_p.exists() else None,
                },
                "coverage_boundary": {
                    "path": "data/evaluations/coverage_boundary_evaluation.json",
                    "sha256": compute_sha256(cov_eval_p) if cov_eval_p.exists() else None,
                },
            },
            "calibrator": {
                "path": "data/models/calibrator_v1.json",
                "sha256": compute_sha256(calibrator_file),
                "status": "CALIBRATION_INSUFFICIENT_DATA",
                "n_samples": 24,
                "note": "Calibrator sample size (N=24) insufficient for statistical calibration claims; flagged CALIBRATION_INSUFFICIENT_DATA.",
            },
            "regulatory_datasets": {
                "qco_orders": {
                    "path": "data/regulatory/qco_orders.jsonl",
                    "sha256": compute_sha256(qco_file),
                    "record_count": count_lines(qco_file),
                },
                "crs_rules": {
                    "path": "data/regulatory/crs_rules.jsonl",
                    "sha256": compute_sha256(crs_file),
                    "record_count": count_lines(crs_file),
                },
                "source_manifest": {
                    "path": "data/regulatory/source_manifest.json",
                    "sha256": compute_sha256(src_manifest),
                },
            },
        },
        "authoritative_evaluation": {
            "evaluation_command": "python scripts/evaluate_recommendation.py --benchmark data/benchmarks/test.jsonl --output-json data/evaluations/test_evaluation.json",
            "evaluated_benchmark": "data/benchmarks/test.jsonl",
            "evaluation_artifact": "data/evaluations/test_evaluation.json",
            "total_queries": test_metrics.get("n_queries", 13),
            "metrics": {
                "retrieval_gold_accuracy_top1": round(test_metrics.get("retrieval_accuracy", 0.0), 4),
                "candidate_recall_at_5": round(test_metrics.get("candidate_recall_at_k", 0.0), 4),
                "verified_primary_rec_accuracy": round(test_metrics.get("primary_accuracy", 0.0), 4),
                "safe_decision_contract_accuracy": round(test_metrics.get("safe_decision_accuracy", 0.0), 4),
                "legacy_raw_decision_match": round(test_metrics.get("decision_accuracy_raw", 0.0), 4),
                "safe_abstention_rate_on_unready": round(test_metrics.get("safe_abstention_rate", 0.0), 4),
                "unsafe_primary_promotion_rate": round(test_metrics.get("unsafe_primary_rate", 0.0), 4),
                "regulatory_mandate_accuracy": round(test_metrics.get("regulatory_accuracy", 0.0), 4),
                "hard_negative_rejection_at_1": round(test_metrics.get("hnrr_at1", 0.0), 4),
                "hard_negative_intrusion_at_5": round(test_metrics.get("hn_intrusion_rate_5", 0.0), 4),
                "hard_negative_intrusion_at_10": round(test_metrics.get("hn_intrusion_rate_10", 0.0), 4),
                "expected_calibration_error_diagnostic": round(test_metrics.get("ece", 0.0), 4),
                "brier_score_diagnostic": round(test_metrics.get("brier_score", 0.0), 4),
            },
        },
        "departments": [ced_dept, etd_dept],
    }

    return release_manifest, ced_dept, etd_dept


def validate_manifest_integrity(manifest_path: Path) -> List[str]:
    """Validate that manifest exists, matches version.py, and matches disk hashes."""
    errors = []
    if not manifest_path.exists():
        return [f"Authoritative release manifest not found at: {manifest_path}"]

    with open(manifest_path, "r", encoding="utf-8") as f:
        committed = json.load(f)

    # 1. Version and Release ID agreement
    if committed.get("release_id") != RELEASE_ID:
        errors.append(f"Release ID mismatch: manifest has '{committed.get('release_id')}', src.version has '{RELEASE_ID}'")
    v = committed.get("versions", {})
    if v.get("engine_version") != ENGINE_VERSION:
        errors.append(f"Engine version mismatch: manifest has '{v.get('engine_version')}', src.version has '{ENGINE_VERSION}'")

    # 2. Check artifacts
    artifacts = committed.get("artifacts", {})

    # Knowledge graph
    kg = artifacts.get("knowledge_graph", {})
    kg_p = PROJECT_ROOT / kg.get("path", "")
    if not kg_p.exists():
        errors.append(f"Knowledge graph file does not exist: {kg_p}")
    else:
        actual_sha = compute_sha256(kg_p)
        if actual_sha != kg.get("sha256"):
            errors.append(f"Knowledge graph SHA mismatch: expected {kg.get('sha256')}, got {actual_sha}")

    # Benchmarks
    benchmarks = artifacts.get("benchmarks", {})
    for b_name, b_meta in benchmarks.items():
        b_p = PROJECT_ROOT / b_meta.get("path", "")
        if not b_p.exists():
            errors.append(f"Benchmark file '{b_name}' does not exist: {b_p}")
        else:
            actual_sha = compute_sha256(b_p)
            if actual_sha != b_meta.get("sha256"):
                errors.append(f"Benchmark '{b_name}' SHA mismatch: expected {b_meta.get('sha256')}, got {actual_sha}")
            actual_count = count_lines(b_p)
            if actual_count != b_meta.get("record_count"):
                errors.append(f"Benchmark '{b_name}' record count mismatch: expected {b_meta.get('record_count')}, got {actual_count}")

    # Calibrator
    cal = artifacts.get("calibrator", {})
    cal_p = PROJECT_ROOT / cal.get("path", "")
    if not cal_p.exists():
        errors.append(f"Calibrator file does not exist: {cal_p}")
    else:
        actual_sha = compute_sha256(cal_p)
        if actual_sha != cal.get("sha256"):
            errors.append(f"Calibrator SHA mismatch: expected {cal.get('sha256')}, got {actual_sha}")

    # Evaluation artifacts
    eval_arts = artifacts.get("evaluation_artifacts", {})
    for e_name, e_meta in eval_arts.items():
        if not e_meta or not e_meta.get("path"):
            continue
        e_p = PROJECT_ROOT / e_meta["path"]
        if not e_p.exists():
            errors.append(f"Evaluation artifact '{e_name}' does not exist: {e_p}")
        else:
            actual_sha = compute_sha256(e_p)
            if actual_sha != e_meta.get("sha256"):
                errors.append(f"Evaluation artifact '{e_name}' SHA mismatch: expected {e_meta.get('sha256')}, got {actual_sha}")

    # Regulatory datasets
    reg = artifacts.get("regulatory_datasets", {})
    for r_name, r_meta in reg.items():
        r_p = PROJECT_ROOT / r_meta.get("path", "")
        if not r_p.exists():
            errors.append(f"Regulatory file '{r_name}' does not exist: {r_p}")
        else:
            actual_sha = compute_sha256(r_p)
            if actual_sha != r_meta.get("sha256"):
                errors.append(f"Regulatory file '{r_name}' SHA mismatch: expected {r_meta.get('sha256')}, got {actual_sha}")

    # Department outputs
    for dept in committed.get("departments", []):
        d_name = dept.get("department")
        inp_p = PROJECT_ROOT / dept.get("input_file", "")
        if not inp_p.exists():
            errors.append(f"Department '{d_name}' input file does not exist: {inp_p}")
        for out_name, out_meta in dept.get("outputs", {}).items():
            out_p = PROJECT_ROOT / out_meta.get("path", "")
            if not out_p.exists():
                errors.append(f"Department '{d_name}' output '{out_name}' does not exist: {out_p}")
            else:
                actual_sha = compute_sha256(out_p)
                if actual_sha != out_meta.get("sha256"):
                    errors.append(f"Department '{d_name}' output '{out_name}' SHA mismatch: expected {out_meta.get('sha256')}, got {actual_sha}")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Authoritative Release Manifest Generator and Validator")
    parser.add_argument("--check", action="store_true", help="Check manifest integrity without modifying files")
    args = parser.parse_args()

    manifests_dir = PROJECT_ROOT / "data" / "manifests"
    release_path = manifests_dir / "standspec_prototype_release.json"

    root_release_path = PROJECT_ROOT / "RELEASE_MANIFEST.json"

    if args.check:
        print(f"Checking manifest integrity against: {release_path}")
        errors = validate_manifest_integrity(release_path)
        if root_release_path.exists():
            root_errors = validate_manifest_integrity(root_release_path)
            errors.extend([f"RELEASE_MANIFEST.json: {e}" for e in root_errors])
        if errors:
            print("\n[FAIL] Manifest Integrity Check FAILED:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print("\n[PASS] Manifest integrity check PASSED! All paths exist and hashes match authoritative data.")
            sys.exit(0)

    # Generate mode
    manifests_dir.mkdir(parents=True, exist_ok=True)
    release_manifest, ced_dept, etd_dept = generate_manifest_data()

    # Preserve committed build timestamp if exists
    if release_path.exists():
        try:
            with open(release_path, "r", encoding="utf-8") as f:
                prev = json.load(f)
                if "build_timestamp" in prev:
                    release_manifest["build_timestamp"] = prev["build_timestamp"]
        except Exception:
            pass

    with open(release_path, "w", encoding="utf-8") as f:
        json.dump(release_manifest, f, indent=2)

    with open(root_release_path, "w", encoding="utf-8") as f:
        json.dump(release_manifest, f, indent=2)

    with open(manifests_dir / "CED_manifest.json", "w", encoding="utf-8") as f:
        json.dump(ced_dept, f, indent=2)

    with open(manifests_dir / "ETD_manifest.json", "w", encoding="utf-8") as f:
        json.dump(etd_dept, f, indent=2)

    print(f"[OK] Authoritative release manifest written to {release_path}")
    print(f"[OK] Central release manifest written to {root_release_path}")
    print(f"Release ID: {RELEASE_ID}")
    print(f"Engine Version: {ENGINE_VERSION}")



if __name__ == "__main__":
    main()
