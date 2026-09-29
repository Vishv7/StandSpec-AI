"""
Retrieval & Decision Error Taxonomy Analysis — StandSpec AI
Audits retrieval misses and decision outcomes against the canonical error taxonomy:
- RETRIEVAL_MISS_ABSENT_FROM_KB
- RETRIEVAL_MISS_UNHYDRATED_STUB
- RETRIEVAL_MISS_LEXICAL_GAP
- RERANKING_DISPLACEMENT
- APPLICABILITY_FALSE_REJECTION
- FALSE_ABSTENTION_THRESHOLD
- WRONG_PRIMARY / WRONG_PART / WRONG_EDITION / WRONG_ROLE
"""

import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.recommendation.engine import StandSpecRecommendationEngine
from src.evaluation.error_taxonomy import classify_evaluation_error, ErrorLabel
from src.evaluation.metrics import compute_comprehensive_metrics


def analyze_errors(
    engine: StandSpecRecommendationEngine,
    benchmark_paths: List[Path],
    output_report_path: Path,
) -> Dict[str, Any]:
    all_queries = []
    all_outputs = []
    query_diagnostics = []
    error_counts = Counter()

    graph = engine.standards_graph

    for bp in benchmark_paths:
        if not bp.exists():
            continue
        with open(bp, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                q = json.loads(line)
                raw_text = (q.get("query") or {}).get("raw_text") or q.get("raw_text") or ""
                qid = q.get("query_id", "Q_TEST")
                eval_date = (q.get("source") or {}).get("evaluation_as_of_date") or "2026-07-15"

                out = engine.recommend(
                    raw_text=raw_text,
                    query_id=qid,
                    evaluation_date=eval_date,
                    top_k=5,
                )

                labels = classify_evaluation_error(q, out, graph=graph)
                for lbl in labels:
                    error_counts[lbl] += 1

                all_queries.append(q)
                all_outputs.append(out)

                golds = [g.get("standard_designation") for g in q.get("gold_standards", [])]
                primary = out.get("primary_recommendation")
                p_desig = primary.get("standard_designation") if primary else None
                cands = [c.get("standard_designation") or c.get("designation") for c in (out.get("candidate_recommendations") or [])]

                query_diagnostics.append({
                    "query_id": qid,
                    "benchmark_file": bp.name,
                    "query_text": raw_text[:80],
                    "gold_standards": golds,
                    "primary_recommendation": p_desig,
                    "decision_state": out.get("decision_state"),
                    "top_candidates": cands[:5],
                    "error_labels": labels,
                })

    metrics = compute_comprehensive_metrics(all_queries, all_outputs)

    report = {
        "analysis_timestamp": "2026-09-30T00:00:00Z",
        "total_queries_evaluated": len(all_queries),
        "benchmarks_evaluated": [bp.name for bp in benchmark_paths],
        "metrics_summary": metrics,
        "error_taxonomy_breakdown": dict(error_counts.most_common()),
        "query_diagnostics": query_diagnostics,
    }

    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def main():
    parser = argparse.ArgumentParser(description="Analyze retrieval errors and evaluate taxonomy")
    parser.add_argument("--benchmark", type=str, default="data/benchmarks/open_world.jsonl")
    parser.add_argument("--output", type=str, default="data/reports/retrieval_error_analysis.json")
    args = parser.parse_args()

    engine = StandSpecRecommendationEngine.from_release()
    bench_p = PROJECT_ROOT / args.benchmark
    out_p = PROJECT_ROOT / args.output

    benchmarks = [bench_p]
    print(f"Running retrieval error taxonomy analysis on {bench_p}...")
    report = analyze_errors(engine, benchmarks, out_p)
    print(f"[OK] Report written to: {out_p}")
    print(f"Total queries: {report['total_queries_evaluated']}")
    print("Taxonomy Breakdown:")
    for lbl, cnt in report["error_taxonomy_breakdown"].items():
        print(f"  - {lbl}: {cnt}")


if __name__ == "__main__":
    main()
