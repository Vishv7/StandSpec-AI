"""
Retrieval Evaluation Script — StandSpec AI (Phase 8 Baseline Measurement)
Evaluates retrieval baselines (BM25, and future dense/hybrid) against benchmark datasets.
Computes multi-gold Recall@1/3/5/10, HitRate@1/3/5/10, MRR, NDCG@10 (full gold set IDCG),
Gold Representability check, and Hard Negative Rejection Rate (HNRR).

Usage:
    python scripts/evaluate_retrieval.py --benchmark data/benchmarks/procurement_benchmark_template.jsonl --graph data/processed/standards_graph.json
"""

import sys
import json
import math
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval.bm25_retriever import BM25Retriever


def compute_dcg(relevances: list[float], k: int) -> float:
    """Compute Discounted Cumulative Gain up to rank k."""
    dcg = 0.0
    for i, rel in enumerate(relevances[:k], 1):
        if rel > 0:
            dcg += rel / math.log2(i + 1)
    return dcg


def compute_idcg(n_gold: int, k: int) -> float:
    """
    Compute Ideal DCG (IDCG) across the complete set of gold standards for the query.
    Assumes binary relevance (1.0 for each gold standard).
    """
    if n_gold <= 0:
        return 0.0
    ideal_ranks = min(n_gold, k)
    return sum(1.0 / math.log2(i + 1) for i in range(1, ideal_ranks + 1))


def check_gold_representability(queries: list[dict], corpus_designations: set[str]) -> dict:
    """
    Check whether gold standards cited in the benchmark actually exist in the corpus.
    Prevents false conclusions when misses are due to standard absence rather than model error.
    """
    all_golds = set()
    for q in queries:
        for g in q.get("gold_standards", []):
            std = g.get("standard_designation")
            if std:
                all_golds.add(std)

    if not all_golds:
        return {
            "total_gold_standards": 0,
            "present_in_corpus": 0,
            "missing_from_corpus": 0,
            "representability_ratio": 1.0,
            "missing_standards": [],
        }

    present = all_golds.intersection(corpus_designations)
    missing = all_golds - corpus_designations
    ratio = len(present) / len(all_golds)

    return {
        "total_gold_standards": len(all_golds),
        "present_in_corpus": len(present),
        "missing_from_corpus": len(missing),
        "representability_ratio": ratio,
        "missing_standards": sorted(missing),
    }


def evaluate_benchmark(benchmark_path: Path, retriever: BM25Retriever, top_k: int = 10, corpus_designations: set[str] = None) -> dict:
    """Run evaluation over a benchmark file."""
    with open(benchmark_path, "r", encoding="utf-8") as f:
        queries = [json.loads(line) for line in f if line.strip() and not line.startswith("#")]

    if not queries:
        return {}

    if corpus_designations:
        corpus_desigs = corpus_designations
    elif hasattr(retriever, "doc_ids"):
        corpus_desigs = set(retriever.doc_ids)
    else:
        corpus_desigs = set()
    representability = check_gold_representability(queries, corpus_desigs)

    n_queries = len(queries)
    recall_at_1_list = []
    recall_at_3_list = []
    recall_at_5_list = []
    recall_at_10_list = []

    hit_at_1_count = 0
    hit_at_3_count = 0
    hit_at_5_count = 0
    hit_at_10_count = 0

    total_reciprocal_rank = 0.0
    total_ndcg = 0.0

    total_hard_negatives = 0
    rejected_hard_negatives = 0

    per_query_results = []

    for q in queries:
        qid = q.get("query_id")
        raw_text = q.get("query", {}).get("raw_text", "")
        gold_standards = [g["standard_designation"] for g in q.get("gold_standards", [])]
        gold_set = set(gold_standards)
        n_gold = len(gold_set)

        hard_negatives = [h["standard_designation"] for h in q.get("hard_negatives", [])]

        retrieved = retriever.retrieve(raw_text, top_k=top_k)
        retrieved_ids = [r["designation"] for r in retrieved]

        # Multi-gold set intersection at K
        def multi_gold_recall(k: int) -> float:
            if n_gold == 0:
                return 1.0
            top_k_set = set(retrieved_ids[:k])
            return len(top_k_set.intersection(gold_set)) / n_gold

        r1 = multi_gold_recall(1)
        r3 = multi_gold_recall(3)
        r5 = multi_gold_recall(5)
        r10 = multi_gold_recall(10)

        recall_at_1_list.append(r1)
        recall_at_3_list.append(r3)
        recall_at_5_list.append(r5)
        recall_at_10_list.append(r10)

        # Hit rate at K (at least 1 gold in top K)
        if any(g in set(retrieved_ids[:1]) for g in gold_set):
            hit_at_1_count += 1
        if any(g in set(retrieved_ids[:3]) for g in gold_set):
            hit_at_3_count += 1
        if any(g in set(retrieved_ids[:5]) for g in gold_set):
            hit_at_5_count += 1
        if any(g in set(retrieved_ids[:10]) for g in gold_set):
            hit_at_10_count += 1

        # MRR: rank of first retrieved gold
        hit_ranks = [retrieved_ids.index(g) + 1 for g in gold_set if g in retrieved_ids]
        first_hit_rank = min(hit_ranks) if hit_ranks else None
        reciprocal_rank = 1.0 / first_hit_rank if first_hit_rank else 0.0
        total_reciprocal_rank += reciprocal_rank

        # Correct NDCG@K: IDCG must use full gold standard set
        relevances = [1.0 if r_id in gold_set else 0.0 for r_id in retrieved_ids]
        dcg = compute_dcg(relevances, top_k)
        idcg = compute_idcg(n_gold, top_k)
        ndcg = dcg / idcg if idcg > 0 else 0.0
        total_ndcg += ndcg

        # Hard negative rejection (Target: HN must not be in top-3)
        top_3_retrieved = set(retrieved_ids[:3])
        for hn in hard_negatives:
            total_hard_negatives += 1
            if hn not in top_3_retrieved:
                rejected_hard_negatives += 1

        per_query_results.append({
            "query_id": qid,
            "first_hit_rank": first_hit_rank,
            "reciprocal_rank": round(reciprocal_rank, 4),
            "recall_at_10": round(r10, 4),
            "ndcg_at_10": round(ndcg, 4),
            "top_retrieved": retrieved_ids[:3],
            "gold_standards": gold_standards,
            "golds_retrieved_in_top_k": sorted(list(set(retrieved_ids[:top_k]).intersection(gold_set))),
        })

    mrr = total_reciprocal_rank / n_queries
    mean_ndcg = total_ndcg / n_queries
    hnrr = rejected_hard_negatives / total_hard_negatives if total_hard_negatives > 0 else 1.0

    return {
        "n_queries": n_queries,
        "gold_representability": representability,
        "recall_at_1": sum(recall_at_1_list) / n_queries,
        "recall_at_3": sum(recall_at_3_list) / n_queries,
        "recall_at_5": sum(recall_at_5_list) / n_queries,
        "recall_at_10": sum(recall_at_10_list) / n_queries,
        "hit_rate_at_1": hit_at_1_count / n_queries,
        "hit_rate_at_3": hit_at_3_count / n_queries,
        "hit_rate_at_5": hit_at_5_count / n_queries,
        "hit_rate_at_10": hit_at_10_count / n_queries,
        "mrr": mrr,
        "ndcg_at_10": mean_ndcg,
        "hard_negatives_evaluated": total_hard_negatives,
        "hnrr": hnrr,
        "per_query_results": per_query_results,
    }


def print_evaluation_report(metrics: dict, benchmark_path: Path):
    print("=" * 70)
    print("StandSpec AI — Retrieval Baseline Evaluation Report")
    print(f"Benchmark: {benchmark_path}")
    print(f"Total Evaluated Queries: {metrics['n_queries']}")
    print("=" * 70)

    rep = metrics.get("gold_representability", {})
    rep_ratio = rep.get("representability_ratio", 1.0)
    print(f"Gold Representability: {rep_ratio:>7.2%} ({rep.get('present_in_corpus', 0)}/{rep.get('total_gold_standards', 0)} standards present in corpus)")
    if rep_ratio < 1.0:
        print("  [WARNING] Benchmark contains gold standards not present in the active corpus!")
        print(f"  Missing standards ({len(rep.get('missing_standards', []))}): {rep.get('missing_standards', [])[:5]}...")
        print("  Retrieval misses for missing standards reflect corpus boundary, not retrieval algorithmic failure.")
    print("-" * 70)

    print(f"Multi-Gold Recall@1:  {metrics['recall_at_1']:>7.2%}  (HitRate@1:  {metrics['hit_rate_at_1']:>7.2%})")
    print(f"Multi-Gold Recall@3:  {metrics['recall_at_3']:>7.2%}  (HitRate@3:  {metrics['hit_rate_at_3']:>7.2%})")
    print(f"Multi-Gold Recall@5:  {metrics['recall_at_5']:>7.2%}  (HitRate@5:  {metrics['hit_rate_at_5']:>7.2%})")
    print(f"Multi-Gold Recall@10: {metrics['recall_at_10']:>7.2%}  (HitRate@10: {metrics['hit_rate_at_10']:>7.2%})")
    print(f"MRR:                  {metrics['mrr']:>7.4f}")
    print(f"NDCG@10 (Full Gold):  {metrics['ndcg_at_10']:>7.4f}")
    print(f"HNRR:                 {metrics['hnrr']:>7.2%}  ({metrics['hard_negatives_evaluated']} hard negatives evaluated)")
    print()

    print("--- Per-Query Breakdown ---")
    for r in metrics["per_query_results"]:
        rank_str = f"Rank {r['first_hit_rank']}" if r['first_hit_rank'] else "MISS"
        hits_summary = f"{len(r['golds_retrieved_in_top_k'])}/{len(r['gold_standards'])} golds"
        print(f"  [{r['query_id']}] {rank_str:<8} | {hits_summary:<12} | R@10: {r['recall_at_10']:.2f} | NDCG@10: {r['ndcg_at_10']:.2f} | Top 3: {r['top_retrieved']}")
    print()


def main():
    parser = argparse.ArgumentParser(description="StandSpec AI Retrieval Evaluator")
    parser.add_argument("--benchmark", "-b", default="data/benchmarks/procurement_benchmark_template.jsonl")
    parser.add_argument("--graph", "-g", default="data/processed/standards_graph.json")
    parser.add_argument("--top-k", type=int, default=10)

    args = parser.parse_args()

    benchmark_path = Path(args.benchmark)
    if not benchmark_path.exists():
        print(f"Error: Benchmark file not found: {benchmark_path}")
        sys.exit(1)

    graph_path = Path(args.graph)
    if not graph_path.exists():
        print(f"Error: Standards graph not found: {graph_path}. Run build_knowledge_graph.py first.")
        sys.exit(1)

    print("Loading standards knowledge graph...")
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    corpus = graph.get("nodes", [])
    corpus_desigs = {n["id"] for n in corpus}
    print(f"Indexing {len(corpus)} standards documents with BM25...")
    retriever = BM25Retriever()
    retriever.index_documents(corpus)

    print(f"Running evaluation on {benchmark_path}...")
    metrics = evaluate_benchmark(benchmark_path, retriever, top_k=args.top_k, corpus_designations=corpus_desigs)
    print_evaluation_report(metrics, benchmark_path)


if __name__ == "__main__":
    main()
