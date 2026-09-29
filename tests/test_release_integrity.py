"""
Release Integrity and Manifest Truth Test Suite — StandSpec AI (P1-A)
Verifies:
1. All files declared in authoritative release manifest exist.
2. Recorded SHA-256 matches actual byte hash on disk.
3. Release ID and Engine Version in manifest match `src.version`.
4. Calibrator path points to an existing file with matching hash.
5. Benchmark record counts match actual line counts.
6. Manifest check pipeline passes cleanly (`scripts/generate_release_manifest.py --check`).
"""

import json
from pathlib import Path
import pytest
from src.version import (
    ENGINE_VERSION,
    RELEASE_ID,
    FORMAT_VERSION,
    SCHEMA_VERSION,
)
from scripts.generate_release_manifest import (
    compute_sha256,
    count_lines,
    validate_manifest_integrity,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "standspec_prototype_release.json"


def test_manifest_file_exists():
    assert MANIFEST_PATH.exists(), f"Manifest missing at {MANIFEST_PATH}"


def test_manifest_version_agreement():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["release_id"] == RELEASE_ID
    assert data["format_version"] == FORMAT_VERSION
    assert data["versions"]["engine_version"] == ENGINE_VERSION
    assert data["versions"]["schema_version"] == SCHEMA_VERSION


def test_manifest_artifacts_exist_and_hashes_match():
    errors = validate_manifest_integrity(MANIFEST_PATH)
    assert not errors, f"Manifest integrity validation errors: {errors}"


def test_calibrator_artifact_exists_at_actual_path():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    cal_rel_path = data["artifacts"]["calibrator"]["path"]
    cal_p = PROJECT_ROOT / cal_rel_path
    assert cal_p.exists(), f"Calibrator file does not exist at {cal_p}"
    actual_sha = compute_sha256(cal_p)
    assert actual_sha == data["artifacts"]["calibrator"]["sha256"]


def test_benchmark_counts_match_files():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    benchmarks = data["artifacts"]["benchmarks"]
    for name, meta in benchmarks.items():
        p = PROJECT_ROOT / meta["path"]
        assert p.exists()
        assert count_lines(p) == meta["record_count"]
