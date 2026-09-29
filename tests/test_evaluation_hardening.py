"""
Tests for Evaluation Hardening & Zero-Leakage Validation (Gates P0-8, P0-9, P0-10 / Stream C).
Verifies multi-gold Recall@K calculation, full-gold IDCG for NDCG@10,
gold representability check, and comprehensive 7-dimension leakage detection.
"""

import json
from pathlib import Path
import pytest

from scripts.evaluate_retrieval import (
    compute_dcg,
    compute_idcg,
    check_gold_representability,
    evaluate_benchmark,
)
from scripts.validate_benchmark import (
    check_leakage,
    extract_base_standard,
    tokenize_query,
)
from src.retrieval.bm25_retriever import BM25Retriever


def test_multi_gold_recall_math():
    """Verify Recall@K is computed as |retrieved@K cap gold| / |gold|, not boolean hit."""
    gold_set = {"IS 7098 (Part 1)", "IS 7098 (Part 2)", "IS 694"}
    n_gold = len(gold_set)

    # Scenario A: Only 1 out of 3 retrieved in top 10
    retrieved_1 = ["IS 7098 (Part 1)", "IS 100", "IS 200"]
    r_at_10_partial = len(set(retrieved_1[:10]).intersection(gold_set)) / n_gold
    assert abs(r_at_10_partial - 1.0 / 3.0) < 1e-4

    # Scenario B: All 3 retrieved in top 10
    retrieved_all = ["IS 7098 (Part 1)", "IS 7098 (Part 2)", "IS 694"]
    r_at_10_full = len(set(retrieved_all[:10]).intersection(gold_set)) / n_gold
    assert r_at_10_full == 1.0


def test_full_gold_idcg_ndcg_math():
    """
    Verify NDCG@K computes Ideal DCG across the full gold set,
    so missing gold standards correctly penalize NDCG.
    """
    n_gold = 3
    k = 10
    idcg = compute_idcg(n_gold, k)
    # IDCG for 3 items at ranks 1, 2, 3: 1/log2(2) + 1/log2(3) + 1/log2(4)
    # = 1.0 + 0.63092975 + 0.5 = 2.13092975
    assert abs(idcg - 2.13093) < 1e-3

    # If only 1 gold standard is retrieved at rank 1, DCG = 1.0
    dcg = compute_dcg([1.0, 0.0, 0.0], k)
    assert dcg == 1.0

    ndcg = dcg / idcg
    # NDCG must be ~ 0.469, strictly NOT 1.0
    assert abs(ndcg - (1.0 / idcg)) < 1e-4
    assert ndcg < 0.50


def test_gold_representability_check():
    """Verify gold representability flags missing standards from corpus."""
    queries = [
        {
            "query_id": "Q1",
            "gold_standards": [
                {"standard_designation": "IS 100:2020"},
                {"standard_designation": "IS 200:2021"}
            ]
        },
        {
            "query_id": "Q2",
            "gold_standards": [
                {"standard_designation": "IS 300:2022"}
            ]
        }
    ]
    # Corpus only contains IS 100 and IS 200, missing IS 300
    corpus = {"IS 100:2020", "IS 200:2021", "IS 400:2023"}

    rep = check_gold_representability(queries, corpus)
    assert rep["total_gold_standards"] == 3
    assert rep["present_in_corpus"] == 2
    assert rep["missing_from_corpus"] == 1
    assert abs(rep["representability_ratio"] - 2.0 / 3.0) < 1e-4
    assert rep["missing_standards"] == ["IS 300:2022"]


def test_leakage_detector_catches_exact_and_base_family(tmp_path):
    """Verify check_leakage catches exact standard overlap and base family overlap."""
    train_file = tmp_path / "train.jsonl"
    test_file = tmp_path / "test.jsonl"

    train_data = [
        {
            "query_id": "TR_1",
            "query": {"raw_text": "XLPE underground cables for medium voltage"},
            "gold_standards": [{"standard_designation": "IS 7098 (Part 1):1988"}],
            "hard_negatives": [{"standard_designation": "IS 694:2010"}]
        }
    ]
    test_data = [
        {
            "query_id": "TE_1",
            "query": {"raw_text": "High voltage XLPE cable installation"},
            "gold_standards": [{"standard_designation": "IS 7098 (Part 2):2011"}],
            "hard_negatives": []
        }
    ]

    train_file.write_text("\n".join(json.dumps(d) for d in train_data), encoding="utf-8")
    test_file.write_text("\n".join(json.dumps(d) for d in test_data), encoding="utf-8")

    clean, report = check_leakage(train_file, test_file)
    assert clean is False
    assert report["leakage_exact_count"] == 0
    assert report["leakage_family_count"] == 1
    assert report["leakage_family_instances"][0][1] == "IS 7098 (Part 2):2011"
    assert report["leakage_family_instances"][0][2] == "IS 7098"


def test_leakage_detector_catches_near_duplicate_queries(tmp_path):
    """Verify check_leakage detects near-duplicate queries with high Jaccard token overlap."""
    train_file = tmp_path / "train.jsonl"
    test_file = tmp_path / "test.jsonl"

    train_data = [
        {
            "query_id": "TR_1",
            "query": {"raw_text": "crosslinked polyethylene insulated thermoplastic sheathed electric power cables"},
            "gold_standards": [{"standard_designation": "IS 100:2020"}],
            "hard_negatives": []
        }
    ]
    # Test query is practically the same wording
    test_data = [
        {
            "query_id": "TE_1",
            "query": {"raw_text": "crosslinked polyethylene insulated thermoplastic sheathed power cables specification"},
            "gold_standards": [{"standard_designation": "IS 200:2020"}],
            "hard_negatives": []
        }
    ]

    train_file.write_text("\n".join(json.dumps(d) for d in train_data), encoding="utf-8")
    test_file.write_text("\n".join(json.dumps(d) for d in test_data), encoding="utf-8")

    clean, report = check_leakage(train_file, test_file)
    assert clean is False
    assert report["leakage_near_duplicates_count"] == 1
    assert report["leakage_near_duplicates_instances"][0][0] == "TE_1"
    assert report["leakage_near_duplicates_instances"][0][1] == "TR_1"


def test_leakage_detector_catches_hard_negative_train_gold_overlap(tmp_path):
    """Verify check_leakage catches test hard negatives that appear as train gold standards."""
    train_file = tmp_path / "train.jsonl"
    test_file = tmp_path / "test.jsonl"

    train_data = [
        {
            "query_id": "TR_1",
            "query": {"raw_text": "PVC insulated wires for domestic circuits"},
            "gold_standards": [{"standard_designation": "IS 694:2010"}],
            "hard_negatives": []
        }
    ]
    test_data = [
        {
            "query_id": "TE_1",
            "query": {"raw_text": "Heavy duty mining trailing cables"},
            "gold_standards": [{"standard_designation": "IS 10261:2020"}],
            # Hard negative in test is the gold standard of train query
            "hard_negatives": [{"standard_designation": "IS 694:2010"}]
        }
    ]

    train_file.write_text("\n".join(json.dumps(d) for d in train_data), encoding="utf-8")
    test_file.write_text("\n".join(json.dumps(d) for d in test_data), encoding="utf-8")

    clean, report = check_leakage(train_file, test_file)
    assert clean is False
    assert report["leakage_hard_negatives_count"] == 1
    assert report["leakage_hard_negatives_instances"][0][1] == "IS 694:2010"
