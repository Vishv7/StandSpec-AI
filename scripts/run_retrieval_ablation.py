"""
Retrieval & Reranking Layer Ablation Script — StandSpec AI
Compares 5 pipeline configurations across identical benchmark queries:
  Stage 1: BM25 Alone (Lexical baseline, no reranking)
  Stage 2: Deterministic Dense Alone (Hashed semantic projection, no reranking)
  Stage 3: Neural Dense Alone (Multilingual embedding model / fallback, no reranking)
  Stage 4: Hybrid RRF (BM25 + Dense RRF fusion, no reranking)
  Stage 5: Full Pipeline (Hybrid RRF + Multi-Signal Cross-Encoder Reranker + Technical Applicability Gating)

Metrics computed per stage:
  - Primary (Top-1) Accuracy
  - Recall@5
  - Recall@10
  - MRR (Mean Reciprocal Rank)
  - Hard Negative Rejection Rate (HNRR@1)
  - HN Intrusion Rate @ 5
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.recommendation.engine import StandSpecRecommendationEngine
from src.evaluation.metrics import (
    compute_raw_retrieval_top1,
    compute_effective_candidate_top1,
    compute_verified_primary_top1,
    compute_recall_at_k,
    compute_mrr,
    compute_comprehensive_metrics,
)


STAGES = [
    {
        "name": "1. BM25 Alone",
        "retriever_mode": "bm25_only",
        "reranker_mode": "none",
        "description": "Pure lexical BM25 retrieval without reranker",
    },
    {
        "name": "2. Deterministic Dense Alone",
        "retriever_mode": "dense_deterministic",
        "reranker_mode": "none",
        "description": "384-d hashed semantic projection without reranker",
    },
    {
        "name": "3. Neural Dense Alone",
        "retriever_mode": "dense_neural",
        "reranker_mode": "none",
        "description": "Multilingual dense neural retriever (or hermetic fallback)",
    },
    {
        "name": "4. Hybrid RRF (BM25 + Dense)",
        "retriever_mode": "hybrid_deterministic",
        "reranker_mode": "none",
        "description": "Reciprocal Rank Fusion (k=60) combining BM25 and Dense",
    },
    {
        "name": "5. Full Pipeline (RRF + Reranker + Gate)",
        "retriever_mode": "hybrid_deterministic",
        "reranker_mode": "rule_based",
        "description": "Hybrid RRF + Multi-Signal Cross-Encoder + 10-Attribute Applicability Gating",
    },
]


def evaluate_stage(stage_cfg: dict, queries: List[dict], graph: dict) -> Dict[str, Any]:
    engine = StandSpecRecommendationEngine(
        standards_graph=graph,
        retriever_mode=stage_cfg["retriever_mode"],
        reranker_mode=stage_cfg["reranker_mode"],
    )

    n_queries = len(queries)
    all_outputs = []
    total_hn = 0
    rejected_hn_at1 = 0
    hn_intrusion_5 = 0

    for q in queries:
        raw_text = q.get("query", {}).get("raw_text", "")
        eval_date = q.get("source", {}).get("evaluation_as_of_date")
        hard_negatives = {h["standard_designation"] for h in q.get("hard_negatives", [])}

        output = engine.recommend(raw_text, evaluation_date=eval_date, top_k=10)
        all_outputs.append(output)

        primary_rec = output.get("primary_recommendation")
        primary_desig = primary_rec.get("standard_designation") if primary_rec else None

        cands = [c.get("standard_designation") for c in output.get("candidate_recommendations", [])]
        if not cands and primary_desig:
            cands = [primary_desig]

        # Hard negatives
        for hn in hard_negatives:
            total_hn += 1
            if primary_desig != hn:
                rejected_hn_at1 += 1
        if any(c in hard_negatives for c in cands[:5]):
            hn_intrusion_5 += 1

    # Authoritative shared metrics
    raw_top1 = compute_raw_retrieval_top1(queries, all_outputs)
    eff_top1 = compute_effective_candidate_top1(queries, all_outputs)
    ver_top1 = compute_verified_primary_top1(queries, all_outputs)
    r5 = compute_recall_at_k(queries, all_outputs, k=5)
    r10 = compute_recall_at_k(queries, all_outputs, k=10)
    mrr_val = compute_mrr(queries, all_outputs)

    return {
        "stage": stage_cfg["name"],
        "retriever_mode": stage_cfg["retriever_mode"],
        "reranker_mode": stage_cfg["reranker_mode"],
        "RAW_RETRIEVAL_TOP1": raw_top1["value"],
        "EFFECTIVE_CANDIDATE_TOP1": eff_top1["value"],
        "VERIFIED_PRIMARY_TOP1": ver_top1["value"],
        "top1_accuracy": eff_top1["value"],
        "recall_at_5": r5["value"],
        "recall_at_10": r10["value"],
        "mrr": mrr_val["value"],
        "hnrr_at1": round(rejected_hn_at1 / total_hn, 4) if total_hn > 0 else 1.0,
        "hn_intrusion_rate_5": round(hn_intrusion_5 / n_queries, 4) if n_queries > 0 else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Retrieval & Reranker Ablation Benchmark")
    parser.add_argument("--benchmark", default="data/benchmarks/val.jsonl", help="Path to benchmark split")
    parser.add_argument("--graph", default="data/processed/standards_graph.json", help="Path to standards graph")
    parser.add_argument("--output", default="data/benchmarks/retrieval_ablation_results.json", help="Path to save results")
    args = parser.parse_args()

    benchmark_path = PROJECT_ROOT / args.benchmark
    graph_path = PROJECT_ROOT / args.graph
    output_path = PROJECT_ROOT / args.output

    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    with open(benchmark_path, "r", encoding="utf-8") as f:
        queries = [json.loads(line) for line in f if line.strip() and not line.startswith("#")]

    print("=" * 95)
    print(f"StandSpec AI — Retrieval & Reranker Ablation Study (P1-D)")
    print(f"Target Benchmark: {args.benchmark} ({len(queries)} queries)")
    print(f"Standards Graph:  {args.graph} ({len(graph.get('nodes', []))} nodes)")
    print("=" * 95)

    results = []
    for stage_cfg in STAGES:
        print(f"Evaluating {stage_cfg['name']}...")
        stage_res = evaluate_stage(stage_cfg, queries, graph)
        results.append(stage_res)

    print("\n" + "=" * 95)
    print(f"{'Stage':<35} | {'RAW_TOP1':<8} | {'EFF_TOP1':<8} | {'VER_TOP1':<8} | {'R@5':<6} | {'MRR':<6} | {'HNRR':<6}")
    print("-" * 95)
    for r in results:
        print(
            f"{r['stage']:<35} | {r['RAW_RETRIEVAL_TOP1']:>7.1%} | {r['EFFECTIVE_CANDIDATE_TOP1']:>7.1%} | "
            f"{r['VERIFIED_PRIMARY_TOP1']:>7.1%} | {r['recall_at_5']:>6.1%} | {r['mrr']:>6.3f} | {r['hnrr_at1']:>6.1%}"
        )
    print("=" * 95)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"benchmark": args.benchmark, "stages": results}, f, indent=2)
    print(f"\nSaved detailed ablation results to: {output_path}")


if __name__ == "__main__":
    main()
