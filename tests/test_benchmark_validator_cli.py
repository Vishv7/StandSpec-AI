"""
CLI regression tests for scripts/validate_benchmark.py.

Covers:
- --strict-isolation fails on its own (no --strict required)
- --temporal-split fails on its own when train dates postdate test dates
- --temporal-split passes on valid chronological split
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.validate_benchmark import validate_file, check_leakage, load_schema


def _make_bench_record(qid="Q_ETD_001", eval_date="2026-01-01",
                       explicitness="implicit", gold_designation="IS 1070:1992",
                       domain="ELECTROTECHNICAL", product_family="Electrical Wires & Cables",
                       org="NTPC Limited", hard_negatives=None):
    if hard_negatives is None:
        hard_negatives = [
            {
                "standard_designation": "IS 7098 (Part 2):2011",
                "hn_class": "HN1",
                "confusability_reason": "similar product category",
                "rejection_reason": "different voltage rating",
                "rejection_evidence_span": "Scope covers only 1.1 kV.",
                "source_tier": 1,
            },
            {
                "standard_designation": "IS 1869:2016",
                "hn_class": "HN4",
                "confusability_reason": "similar title",
                "rejection_reason": "different scope",
                "rejection_evidence_span": "Section 3.2 notes.",
                "source_tier": 1,
            },
        ]
    return {
        "query_id": qid,
        "schema_version": "2.1",
        "dataset_split": "C_validation",
        "source": {
            "type": "gem_procurement",
            "organization": org,
            "tender_id": "T001",
            "tender_publication_date": "2026-01-01",
            "evaluation_as_of_date": eval_date,
            "portal_url": "https://example.com/tender",
        },
        "query": {
            "raw_text": f"Supply of {product_family} for {domain} applications",
            "language": "en",
            "domain": domain,
            "product_family": product_family,
        },
        "benchmark_dimensions": {
            "query_explicitness": explicitness,
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR",
        },
        "technical_requirements": {
            "product": "Cable",
            "scope_keywords": ["cable"],
            "target_product": "Cable",
        },
        "gold_standards": [
            {
                "standard_designation": gold_designation,
                "applicability": "primary_product",
                "reason": "Mandatory safety code.",
                "evidence_span": "Clause 5: cable must comply.",
                "relationship_obligation": "MANDATORY",
                "mandatory_by_regulation": True,
            }
        ],
        "hard_negatives": hard_negatives,
        "version_requirement": {
            "policy": "latest_active_only",
            "acceptable_years": ["1992"],
        },
        "certification_requirement": {
            "regulatory_status": "MANDATORY",
        },
        "expected_decision": {
            "query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "expected_abstention_reason": None,
        },
        "expert_review": {
            "reviewers_count": 2,
            "agreement_status": "unanimous",
        },
    }


def _write_jsonl(path: Path, records: list):
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class TestStrictIsolation:
    """--strict-isolation must cause failure on its own when lexical leakage is present."""

    def test_strict_isolation_fails_on_leak_without_strict_flag(self, tmp_path):
        """A benchmark with lexical leakage in an implicit query must fail with --strict-isolation alone."""
        rec = _make_bench_record(
            qid="Q_ETD_001",
            eval_date="2026-01-01",
            explicitness="implicit",
            gold_designation="IS 7098:2020",
        )
        rec["query"]["raw_text"] = "Supply of IS 7098 compliant power cables"

        bench_path = tmp_path / "leak.jsonl"
        _write_jsonl(bench_path, [rec])

        schema = load_schema()
        success, metrics = validate_file(bench_path, schema, strict=False, strict_isolation=True)

        assert success is False, "strict_isolation should fail on lexical leakage without --strict"
        assert metrics["lexical_leakage_count"] == 1
        assert any("is 7098" in e.lower() for e in metrics["errors"])

    def test_strict_isolation_passes_when_no_leak(self, tmp_path):
        """An implicit query that does NOT mention the target standard should pass."""
        rec = _make_bench_record(
            qid="Q_ETD_002",
            eval_date="2026-01-01",
            explicitness="implicit",
            gold_designation="IS 7098:2020",
        )
        rec["query"]["raw_text"] = "Supply of power cables for underground installation"

        bench_path = tmp_path / "clean.jsonl"
        _write_jsonl(bench_path, [rec])

        schema = load_schema()
        success, metrics = validate_file(bench_path, schema, strict=False, strict_isolation=True)

        assert success is True
        assert metrics["lexical_leakage_count"] == 0


class TestTemporalSplit:
    """--temporal-split must enforce chronological ordering of train vs test evaluation dates."""

    def test_valid_temporal_split_passes(self, tmp_path):
        """Train dates older than test dates should pass."""
        train_rec = _make_bench_record(qid="Q_ETD_001", eval_date="2026-05-01",
                                       gold_designation="IS 1070:1992",
                                       domain="ELECTROTECHNICAL", product_family="Cables",
                                       org="NTPC Limited")
        test_rec = _make_bench_record(qid="Q_ETD_002", eval_date="2026-09-01",
                                       gold_designation="IS 16738:2018",
                                       domain="CIVIL_ENGINEERING", product_family="Concrete",
                                       org="IIT Delhi")

        train_path = tmp_path / "train.jsonl"
        test_path = tmp_path / "test.jsonl"
        _write_jsonl(train_path, [train_rec])
        _write_jsonl(test_path, [test_rec])

        clean, report = check_leakage(train_path, test_path, temporal_split=True)
        assert clean is True
        assert report["temporal_violations_count"] == 0

    def test_temporal_split_fails_on_forward_leakage(self, tmp_path):
        """Train eval date newer than test eval date must fail."""
        train_rec = _make_bench_record(qid="Q_ETD_001", eval_date="2026-09-15",
                                       gold_designation="IS 16738:2018",
                                       domain="ELECTROTECHNICAL", product_family="Cables",
                                       org="NTPC Limited")
        test_rec = _make_bench_record(qid="Q_ETD_002", eval_date="2026-01-15",
                                       gold_designation="IS 1070:1992",
                                       domain="CIVIL_ENGINEERING", product_family="Concrete",
                                       org="IIT Delhi")

        train_path = tmp_path / "train.jsonl"
        test_path = tmp_path / "test.jsonl"
        _write_jsonl(train_path, [train_rec])
        _write_jsonl(test_path, [test_rec])

        clean, report = check_leakage(train_path, test_path, temporal_split=True)
        assert clean is False
        assert report["temporal_violations_count"] == 1
        assert "Temporal leakage" in report["temporal_violations"][0]

    def test_temporal_split_no_violation_when_not_requested(self, tmp_path):
        """Without --temporal-split, date ordering should not matter."""
        train_rec = _make_bench_record(qid="Q_ETD_001", eval_date="2026-09-15",
                                       gold_designation="IS 16738:2018",
                                       domain="ELECTROTECHNICAL", product_family="Cables",
                                       org="NTPC Limited")
        test_rec = _make_bench_record(qid="Q_ETD_002", eval_date="2026-01-15",
                                       gold_designation="IS 1070:1992",
                                       domain="CIVIL_ENGINEERING", product_family="Concrete",
                                       org="IIT Delhi")

        train_path = tmp_path / "train.jsonl"
        test_path = tmp_path / "test.jsonl"
        _write_jsonl(train_path, [train_rec])
        _write_jsonl(test_path, [test_rec])

        clean, report = check_leakage(train_path, test_path, temporal_split=False)
        assert report["temporal_violations_count"] == 0
        assert clean is True
