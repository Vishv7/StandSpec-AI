"""
Open-World Recommendation Generalization Evaluation Script — StandSpec AI
Evaluates the complete recommendation engine on unseen open-world queries:
Paraphrase, Compositional, Multilingual, Long Clause, and Conflict/Boundary subsets.

Computes:
- Candidate Recall@1, Recall@5, Recall@10
- Effective Candidate Top-1 Accuracy (including review candidates)
- Verified Primary Recommendation Accuracy
- Safe Decision Accuracy
- Safe Abstention Rate
- Authoritative Safety Metrics (wrong primary promotion rate, etc.)
- Per-subset performance breakdown
- Error classification using canonical error taxonomy
"""

import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.recommendation.engine import StandSpecRecommendationEngine
from src.evaluation.metrics import (
    compute_raw_retrieval_top1,
    compute_effective_candidate_top1,
    compute_verified_primary_top1,
    compute_recall_at_k,
    compute_mrr,
    compute_safety_metrics,
    is_primary_unsupported,
    is_primary_wrong_role,
    is_primary_wrong_edition,
)
from src.evaluation.error_taxonomy import classify_evaluation_error


def determine_subset(qid: str) -> str:
    if "_OWP_" in qid:
        return "paraphrase"
    elif "_OWC_" in qid:
        return "compositional"
    elif "_OWM_" in qid:
        return "multilingual"
    elif "_OWL_" in qid:
        return "long_clause"
    elif "_OWX_" in qid:
        return "conflict"
    return "other"


def evaluate_open_world(benchmark_path: Path, graph_path: Path, top_k: int = 5) -> dict:
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    with open(benchmark_path, "r", encoding="utf-8") as f:
        queries = [json.loads(line) for line in f if line.strip() and not line.startswith("#")]

    engine = StandSpecRecommendationEngine(graph)

    total_queries = len(queries)
    primary_matches = 0
    retrieval_matches = 0
    candidate_hits_at_5 = 0
    candidate_hits_at_10 = 0
    safe_decision_matches = 0
    safe_abstentions_count = 0
    queries_needing_abstention = 0

    per_query_results = []
    all_outputs = []
    subset_stats = defaultdict(lambda: {
        "total": 0,
        "primary_matches": 0,
        "retrieval_matches": 0,
        "hits_at_5": 0,
        "safe_decision_matches": 0,
        "safe_abstentions": 0,
        "needs_abstention": 0,
    })

    for q in queries:
        qid = q.get("query_id", "")
        subset_name = determine_subset(qid)
        raw_text = q.get("query", {}).get("raw_text", "")
        eval_date = q.get("source", {}).get("evaluation_as_of_date")
        expected_golds = {g["standard_designation"] for g in q.get("gold_standards", [])}
        expected_decision = q.get("expected_decision", {}).get("query_level_state")
        cov_state = q.get("prototype_coverage_state") or q.get("expected_coverage_state", "IN_PROTOTYPE_COVERAGE")

        output = engine.recommend(raw_text, evaluation_date=eval_date, top_k=top_k)
        all_outputs.append(output)

        decision_state = output["decision_state"]
        primary_rec = output["primary_recommendation"]
        review_cand = output.get("review_candidate")
        primary_desig = primary_rec["standard_designation"] if primary_rec else None
        top_effective_desig = primary_desig or (review_cand["standard_designation"] if review_cand else None)

        # 1. Primary Recommendation Accuracy (Verified)
        primary_correct = primary_desig in expected_golds if primary_desig else False
        if primary_correct:
            primary_matches += 1
            subset_stats[subset_name]["primary_matches"] += 1

        # 2. Retrieval Gold Match (Top effective candidate matches gold)
        retrieval_correct = top_effective_desig in expected_golds if top_effective_desig else False
        if retrieval_correct:
            retrieval_matches += 1
            subset_stats[subset_name]["retrieval_matches"] += 1

        # 3. Candidate Recall@5 and Recall@10
        candidate_list = [c["standard_designation"] for c in output.get("candidate_recommendations", [])]
        if review_cand and review_cand["standard_designation"] not in candidate_list:
            candidate_list.insert(0, review_cand["standard_designation"])

        hit_5 = len(set(candidate_list[:5]).intersection(expected_golds)) > 0
        hit_10 = len(set(candidate_list[:10]).intersection(expected_golds)) > 0
        if hit_5:
            candidate_hits_at_5 += 1
            subset_stats[subset_name]["hits_at_5"] += 1
        if hit_10:
            candidate_hits_at_10 += 1

        # 4. Safe Decision Contract
        gold_desig = next(iter(expected_golds)) if expected_golds else None
        gold_node = next((n for n in graph.get("nodes", []) if n.get("designation") == gold_desig), None)
        gold_has_scope = bool((gold_node.get("scope") or "").strip()) if gold_node else False
        if "gold_recommendation_ready" in q:
            gold_ready = bool(q["gold_recommendation_ready"])
        elif "gold_in_scope" in q:
            gold_ready = bool(q["gold_in_scope"])
        else:
            gold_ready = gold_has_scope

        if q.get("expected_safe_decision"):
            expected_safe_decision = q["expected_safe_decision"]
        elif not gold_ready:
            expected_safe_decision = "EXPERT_REVIEW_REQUIRED" if expected_golds else (expected_decision or "INSUFFICIENT_INFORMATION")
        else:
            expected_safe_decision = expected_decision or "PRIMARY_RECOMMENDATION_AVAILABLE"

        safe_decision_correct = (decision_state == expected_safe_decision)
        if safe_decision_correct:
            safe_decision_matches += 1
            subset_stats[subset_name]["safe_decision_matches"] += 1

        # Safe Abstention Tracking
        needs_abstention = (not gold_ready) or (expected_decision in ("INSUFFICIENT_INFORMATION", "OUTSIDE_PROTOTYPE_COVERAGE", "NO_CONFIDENT_MATCH"))
        if needs_abstention:
            queries_needing_abstention += 1
            subset_stats[subset_name]["needs_abstention"] += 1
            if decision_state in ("EXPERT_REVIEW_REQUIRED", "INSUFFICIENT_INFORMATION", "OUTSIDE_PROTOTYPE_COVERAGE", "NO_CONFIDENT_MATCH", "CONDITIONAL_RECOMMENDATION", "MULTIPLE_POSSIBLE_STANDARDS"):
                safe_abstentions_count += 1
                subset_stats[subset_name]["safe_abstentions"] += 1

        subset_stats[subset_name]["total"] += 1

        # Error classification
        error_class = classify_evaluation_error(q, output, graph)

        # Detect per-query safety attributes
        is_in_scope = (cov_state == "IN_PROTOTYPE_COVERAGE" and len(expected_golds) > 0)
        is_wrong_primary = bool(primary_rec and ((is_in_scope and primary_desig not in expected_golds) or (not is_in_scope)))

        per_query_results.append({
            "query_id": qid,
            "subset": subset_name,
            "decision_state": decision_state,
            "expected_decision": expected_decision,
            "expected_safe_decision": expected_safe_decision,
            "primary_recommendation": primary_desig,
            "review_candidate": (review_cand.get("standard_designation") if review_cand else None),
            "expected_golds": list(expected_golds),
            "retrieval_correct": retrieval_correct,
            "safe_decision_correct": safe_decision_correct,
            "primary_correct": primary_correct,
            "wrong_primary": is_wrong_primary,
            "error_classifications": error_class if isinstance(error_class, list) else ([error_class] if error_class else []),
            "hit_in_top_5": hit_5,
            "hit_in_top_10": hit_10,
        })

    # Metrics
    raw_top1_res = compute_raw_retrieval_top1(queries, all_outputs)
    eff_top1_res = compute_effective_candidate_top1(queries, all_outputs)
    ver_top1_res = compute_verified_primary_top1(queries, all_outputs)
    mrr_res = compute_mrr(queries, all_outputs)
    safety_res = compute_safety_metrics(queries, all_outputs)

    # Compile subset summaries
    subset_summary = {}
    for sub, s in subset_stats.items():
        tot = s["total"]
        subset_summary[sub] = {
            "total_queries": tot,
            "effective_top1_accuracy": round(s["retrieval_matches"] / tot, 4) if tot > 0 else 0.0,
            "verified_primary_accuracy": round(s["primary_matches"] / tot, 4) if tot > 0 else 0.0,
            "recall_at_5": round(s["hits_at_5"] / tot, 4) if tot > 0 else 0.0,
            "safe_decision_accuracy": round(s["safe_decision_matches"] / tot, 4) if tot > 0 else 0.0,
            "safe_abstention_rate": round(s["safe_abstentions"] / s["needs_abstention"], 4) if s["needs_abstention"] > 0 else 1.0,
        }

    return {
        "n_queries": total_queries,
        "RAW_RETRIEVAL_TOP1": raw_top1_res["value"],
        "EFFECTIVE_CANDIDATE_TOP1": eff_top1_res["value"],
        "VERIFIED_PRIMARY_TOP1": ver_top1_res["value"],
        "MRR": mrr_res["value"],
        "candidate_recall_at_5": candidate_hits_at_5 / total_queries if total_queries > 0 else 0.0,
        "candidate_recall_at_10": candidate_hits_at_10 / total_queries if total_queries > 0 else 0.0,
        "safe_decision_accuracy": safe_decision_matches / total_queries if total_queries > 0 else 0.0,
        "safe_abstention_rate": safe_abstentions_count / queries_needing_abstention if queries_needing_abstention > 0 else 1.0,
        "safety_metrics": {
            "WRONG_PRIMARY_PROMOTION_RATE": safety_res["wrong_primary_promotion_rate"],
            "UNSUPPORTED_PRIMARY_PROMOTION_RATE": safety_res["unsupported_primary_promotion_rate"],
            "WRONG_ROLE_PRIMARY_RATE": safety_res["wrong_role_primary_rate"],
            "WRONG_EDITION_PRIMARY_RATE": safety_res["wrong_edition_primary_rate"],
            "SAFE_PRIMARY_RATE": safety_res["safe_primary_rate"],
            "UNSAFE_PRIMARY_RATE": safety_res["unsafe_primary_rate"],
            "SAFE_DECISION_ACCURACY": safety_res["safe_decision_accuracy"],
            "SAFE_ABSTENTION_RATE": safety_res["safe_abstention_rate"],
        },
        "subset_breakdown": subset_summary,
        "per_query_results": per_query_results,
    }


def print_report(res: dict, title: str = "StandSpec AI — Open-World Evaluation Report") -> None:
    print("\n" + "=" * 76)
    print(f"  {title}")
    print("=" * 76)
    print(f"Total Queries Evaluated:               {res['n_queries']}")
    print(f"RAW RETRIEVAL TOP-1:                   {res['RAW_RETRIEVAL_TOP1'] * 100:.2f}%")
    print(f"EFFECTIVE CANDIDATE TOP-1:             {res['EFFECTIVE_CANDIDATE_TOP1'] * 100:.2f}%")
    print(f"VERIFIED PRIMARY TOP-1:                {res['VERIFIED_PRIMARY_TOP1'] * 100:.2f}%")
    print(f"MRR:                                   {res['MRR']:.4f}")
    print(f"CANDIDATE RECALL@5:                    {res['candidate_recall_at_5'] * 100:.2f}%")
    print(f"CANDIDATE RECALL@10:                   {res['candidate_recall_at_10'] * 100:.2f}%")
    print(f"SAFE DECISION ACCURACY:                {res['safe_decision_accuracy'] * 100:.2f}%")
    print(f"SAFE ABSTENTION RATE:                  {res['safe_abstention_rate'] * 100:.2f}%")
    print("-" * 76)
    sm = res["safety_metrics"]
    print("  Authoritative Safety Metrics:")
    print(f"  - WRONG_PRIMARY_PROMOTION_RATE:      {sm['WRONG_PRIMARY_PROMOTION_RATE'] * 100:.2f}%")
    print(f"  - UNSUPPORTED_PRIMARY_PROMOTION_RATE: {sm['UNSUPPORTED_PRIMARY_PROMOTION_RATE'] * 100:.2f}%")
    print(f"  - WRONG_ROLE_PRIMARY_RATE:           {sm['WRONG_ROLE_PRIMARY_RATE'] * 100:.2f}%")
    print(f"  - WRONG_EDITION_PRIMARY_RATE:        {sm['WRONG_EDITION_PRIMARY_RATE'] * 100:.2f}%")
    print(f"  - SAFE_PRIMARY_RATE:                 {sm['SAFE_PRIMARY_RATE'] * 100:.2f}%")
    print(f"  - UNSAFE_PRIMARY_RATE:               {sm['UNSAFE_PRIMARY_RATE'] * 100:.2f}%")
    print("-" * 76)
    print("  Subset Performance Breakdown:")
    print(f"  {'Subset':<16} {'Queries':<8} {'Eff.Top1':<10} {'Ver.Prim':<10} {'Rec@5':<10} {'SafeDec':<10} {'SafeAbst':<10}")
    print("  " + "-" * 72)
    for sub, data in res["subset_breakdown"].items():
        print(f"  {sub:<16} {data['total_queries']:<8} {data['effective_top1_accuracy']*100:>6.1f}%   {data['verified_primary_accuracy']*100:>6.1f}%   {data['recall_at_5']*100:>6.1f}%   {data['safe_decision_accuracy']*100:>6.1f}%   {data['safe_abstention_rate']*100:>6.1f}%")
    print("=" * 76)


def main():
    parser = argparse.ArgumentParser(description="Evaluate StandSpec AI on Open-World Benchmarks")
    parser.add_argument("--benchmark", type=Path, default=PROJECT_ROOT / "data" / "benchmarks" / "open_world.jsonl")
    parser.add_argument("--graph", type=Path, default=PROJECT_ROOT / "data" / "processed" / "standards_graph.json")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "evaluations" / "open_world_evaluation.json")
    args = parser.parse_args()

    results = evaluate_open_world(args.benchmark, args.graph, top_k=args.top_k)
    print_report(results)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nDetailed evaluation report saved to {args.output}")


if __name__ == "__main__":
    main()
