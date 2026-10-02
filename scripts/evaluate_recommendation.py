"""
End-to-End Recommendation Evaluation Script — StandSpec AI
Evaluates the complete recommendation pipeline:
Requirement Extraction -> Hybrid Retrieval -> RRF -> Graph Expansion ->
Cross-Encoder Reranking -> Technical Applicability -> Lifecycle Gate ->
Regulatory Gate -> Two-Tier Decision State.

Evaluates against validation benchmark dataset (val.jsonl) with the test set remaining strictly locked.
"""

import sys
import json
import argparse
from pathlib import Path

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
    compute_comprehensive_metrics,
)
def evaluate_engine_on_benchmark(benchmark_path: Path, graph_path: Path, top_k: int = 5) -> dict:
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
    in_scope_queries = 0
    in_scope_primary_matches = 0
    outside_cov_queries = 0
    outside_cov_matches = 0
    decision_matches = 0
    safe_decision_matches = 0
    regulatory_matches = 0
    total_hard_negatives = 0
    rejected_hard_negatives_at1 = 0
    hn_intrusion_5_queries = 0
    hn_intrusion_10_queries = 0
    all_hn_ranks = []
    conf_probs = []
    actual_labels = []

    unsafe_primary_count = 0
    queries_with_unready_gold = 0
    safe_abstentions_count = 0

    per_query_results = []
    all_outputs = []

    for q in queries:
        qid = q.get("query_id")
        raw_text = q.get("query", {}).get("raw_text", "")
        eval_date = q.get("source", {}).get("evaluation_as_of_date")
        expected_golds = {g["standard_designation"] for g in q.get("gold_standards", [])}
        expected_decision = q.get("expected_decision", {}).get("query_level_state")
        expected_reg = q.get("certification_requirement", {}).get("regulatory_status")
        hard_negatives = {h["standard_designation"] for h in q.get("hard_negatives", [])}
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

        # 1b. In-Scope / Outside-Coverage Accounting
        if cov_state == "IN_PROTOTYPE_COVERAGE":
            in_scope_queries += 1
            if primary_correct:
                in_scope_primary_matches += 1
        else:
            outside_cov_queries += 1
            if decision_state in ("OUTSIDE_PROTOTYPE_COVERAGE", "NO_CONFIDENT_MATCH"):
                outside_cov_matches += 1

        # 1c. Retrieval Gold Match (Top effective candidate matches gold)
        retrieval_correct = top_effective_desig in expected_golds if top_effective_desig else False
        if retrieval_correct:
            retrieval_matches += 1

        # 2. Candidate Recall@5 and Recall@10
        candidate_list = [c["standard_designation"] for c in output.get("candidate_recommendations", [])]
        if review_cand and review_cand["standard_designation"] not in candidate_list:
            candidate_list.insert(0, review_cand["standard_designation"])
        
        hit_5 = len(set(candidate_list[:5]).intersection(expected_golds)) > 0
        hit_10 = len(set(candidate_list[:10]).intersection(expected_golds)) > 0
        if hit_5:
            candidate_hits_at_5 += 1
        if hit_10:
            candidate_hits_at_10 += 1

        # 3. Two-Tier Decision State Match (Raw legacy benchmark label)
        decision_correct = (decision_state == expected_decision)
        if decision_correct:
            decision_matches += 1

        # 3b. Safe Decision Contract (Evidence-grounded expected decision)
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
            expected_safe_decision = "EXPERT_REVIEW_REQUIRED"
        else:
            expected_safe_decision = expected_decision or "PRIMARY_RECOMMENDATION_AVAILABLE"

        safe_decision_correct = (decision_state == expected_safe_decision)
        if safe_decision_correct:
            safe_decision_matches += 1

        # 3c. Unsafe Primary Tracking (Must be 0.0%)
        if not gold_ready and primary_rec is not None and decision_state == "PRIMARY_RECOMMENDATION_AVAILABLE":
            unsafe_primary_count += 1

        # 3d. Safe Abstention Tracking
        if not gold_ready:
            queries_with_unready_gold += 1
            if decision_state in ("EXPERT_REVIEW_REQUIRED", "INSUFFICIENT_INFORMATION", "CONDITIONAL_RECOMMENDATION", "MULTIPLE_POSSIBLE_STANDARDS"):
                safe_abstentions_count += 1

        # 4. Regulatory Status Match
        rec_for_reg = primary_rec or review_cand
        if rec_for_reg:
            reg_dict = rec_for_reg.get("regulatory") or {}
            reg_status = reg_dict.get("state") or reg_dict.get("regulatory_state")
            if (expected_reg == "MANDATORY" and reg_status in ("MANDATORY_CONFIRMED", "MANDATORY_CONDITIONALLY_APPLICABLE")) or (
                expected_reg != "MANDATORY" and reg_status not in ("MANDATORY_CONFIRMED", "MANDATORY_CONDITIONALLY_APPLICABLE")
            ):
                regulatory_matches += 1

        # 5. Hard Negative Intrusion & Rejection Tracking
        query_candidates = [c.get("standard_designation") for c in output.get("candidate_recommendations", [])]
        has_hn_in_top5 = any(c in hard_negatives for c in query_candidates[:5])
        has_hn_in_top10 = any(c in hard_negatives for c in query_candidates[:10])
        if has_hn_in_top5:
            hn_intrusion_5_queries += 1
        if has_hn_in_top10:
            hn_intrusion_10_queries += 1

        for hn in hard_negatives:
            total_hard_negatives += 1
            if top_effective_desig != hn:
                rejected_hard_negatives_at1 += 1
            if hn in query_candidates:
                rank = query_candidates.index(hn) + 1
                all_hn_ranks.append(rank)

        cal_prob = (output.get("calibration") or {}).get("calibrated_probability") or (
            primary_rec.get("confidence_score", 0.0) if primary_rec else 0.0
        )
        conf_probs.append(cal_prob)
        actual_labels.append(1 if retrieval_correct else 0)

        # Detect per-query safety attributes
        cov_state = q.get("expected_coverage_state", "IN_PROTOTYPE_COVERAGE")
        is_in_scope = (cov_state == "IN_PROTOTYPE_COVERAGE" and len(expected_golds) > 0)
        is_wrong_primary = bool(primary_rec and ((is_in_scope and primary_desig not in expected_golds) or (not is_in_scope)))
        is_unsupported = is_primary_unsupported(primary_rec) if primary_rec else False
        is_wrong_role = is_primary_wrong_role(primary_rec) if primary_rec else False
        is_wrong_edition = is_primary_wrong_edition(primary_rec) if primary_rec else False

        per_query_results.append({
            "query_id": qid,
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
            "unsupported_primary": is_unsupported,
            "wrong_role": is_wrong_role,
            "wrong_edition": is_wrong_edition,
            "hit_in_top_k": hit_5,
            "confidence": primary_rec["confidence_score"] if primary_rec else (review_cand.get("confidence_score", 0.0) if review_cand else 0.0),
            "calibrated_prob": cal_prob,
        })

    hnrr_at1 = rejected_hard_negatives_at1 / total_hard_negatives if total_hard_negatives > 0 else 1.0
    hn_intrusion_rate_5 = hn_intrusion_5_queries / total_queries if total_queries > 0 else 0.0
    hn_intrusion_rate_10 = hn_intrusion_10_queries / total_queries if total_queries > 0 else 0.0
    mean_hn_rank = sum(all_hn_ranks) / len(all_hn_ranks) if all_hn_ranks else float("inf")
    worst_hn_rank = min(all_hn_ranks) if all_hn_ranks else float("inf")

    # Calibration metrics
    from src.calibration.calibrator import compute_ece, compute_brier_score
    ece_val = compute_ece(conf_probs, actual_labels, n_bins=5)
    brier_val = compute_brier_score(conf_probs, actual_labels)

    # Compute authoritative shared metrics via src.evaluation.metrics
    raw_top1_res = compute_raw_retrieval_top1(queries, all_outputs)
    eff_top1_res = compute_effective_candidate_top1(queries, all_outputs)
    ver_top1_res = compute_verified_primary_top1(queries, all_outputs)
    mrr_res = compute_mrr(queries, all_outputs)
    safety_res = compute_safety_metrics(queries, all_outputs)

    return {
        "n_queries": total_queries,
        "RAW_RETRIEVAL_TOP1": raw_top1_res["value"],
        "EFFECTIVE_CANDIDATE_TOP1": eff_top1_res["value"],
        "VERIFIED_PRIMARY_TOP1": ver_top1_res["value"],
        "MRR": mrr_res["value"],
        "retrieval_accuracy": eff_top1_res["value"],
        "candidate_recall_at_k": candidate_hits_at_5 / total_queries if total_queries > 0 else 0.0,
        "candidate_recall_at_5": candidate_hits_at_5 / total_queries if total_queries > 0 else 0.0,
        "candidate_recall_at_10": candidate_hits_at_10 / total_queries if total_queries > 0 else 0.0,
        "primary_accuracy": ver_top1_res["value"],
        "in_scope_primary_accuracy": in_scope_primary_matches / in_scope_queries if in_scope_queries > 0 else 0.0,
        "outside_coverage_accuracy": outside_cov_matches / outside_cov_queries if outside_cov_queries > 0 else 1.0,
        "decision_accuracy_raw": decision_matches / total_queries if total_queries > 0 else 0.0,
        "safe_decision_accuracy": safety_res["safe_decision_accuracy"],
        "safe_abstention_rate": safety_res["safe_abstention_rate"],
        "unsafe_primary_rate": safety_res["unsafe_primary_rate"],
        "wrong_primary_promotion_rate": safety_res["wrong_primary_promotion_rate"],
        "unsupported_primary_promotion_rate": safety_res["unsupported_primary_promotion_rate"],
        "wrong_role_primary_rate": safety_res["wrong_role_primary_rate"],
        "wrong_part_primary_rate": safety_res["wrong_part_primary_rate"],
        "wrong_edition_primary_rate": safety_res["wrong_edition_primary_rate"],
        "regulatory_false_assertion_rate": safety_res["regulatory_false_assertion_rate"],
        "safe_primary_rate": safety_res["safe_primary_rate"],
        "regulatory_accuracy": regulatory_matches / total_queries if total_queries > 0 else 0.0,
        "hnrr_at1": hnrr_at1,
        "hn_intrusion_rate_5": hn_intrusion_rate_5,
        "hn_intrusion_rate_10": hn_intrusion_rate_10,
        "mean_hn_rank": mean_hn_rank,
        "worst_hn_rank": worst_hn_rank,
        "total_hard_negatives": total_hard_negatives,
        "ece": ece_val,
        "brier_score": brier_val,
        "per_query_results": per_query_results,
    }


def print_report(results: dict, benchmark_path: Path):
    print("=" * 70)
    print("StandSpec AI — End-to-End Recommendation Engine Evaluation (P1-E)")
    print(f"Target Benchmark: {benchmark_path}")
    print(f"Total Evaluated Queries: {results['n_queries']}")
    print("=" * 70)
    print("--- 3 Authoritative Top-1 Metrics (P1-D Standard) ---")
    print(f"RAW_RETRIEVAL_TOP1:       {results['RAW_RETRIEVAL_TOP1']:>7.2%}")
    print(f"EFFECTIVE_CANDIDATE_TOP1: {results['EFFECTIVE_CANDIDATE_TOP1']:>7.2%}")
    print(f"VERIFIED_PRIMARY_TOP1:    {results['VERIFIED_PRIMARY_TOP1']:>7.2%}")
    print("-" * 70)
    print("--- Authoritative Safety Metrics (P1-E Standard) ---")
    print(f"WRONG_PRIMARY_PROMOTION_RATE:       {results.get('wrong_primary_promotion_rate', 0.0):>7.2%}")
    print(f"UNSUPPORTED_PRIMARY_PROMOTION_RATE: {results.get('unsupported_primary_promotion_rate', 0.0):>7.2%}")
    print(f"WRONG_ROLE_PRIMARY_RATE:            {results.get('wrong_role_primary_rate', 0.0):>7.2%}")
    print(f"WRONG_PART_PRIMARY_RATE:            {results.get('wrong_part_primary_rate', 0.0):>7.2%}")
    print(f"WRONG_EDITION_PRIMARY_RATE:         {results.get('wrong_edition_primary_rate', 0.0):>7.2%}")
    print(f"REGULATORY_FALSE_ASSERTION_RATE:    {results.get('regulatory_false_assertion_rate', 0.0):>7.2%}")
    safe_prim = results.get('safe_primary_rate')
    safe_prim_str = f"{safe_prim:>7.2%}" if safe_prim is not None else "    N/A"
    safe_abst = results.get('safe_abstention_rate')
    safe_abst_str = f"{safe_abst:>7.2%}" if safe_abst is not None else "    N/A"

    print(f"SAFE_PRIMARY_RATE:                  {safe_prim_str}")
    print(f"COMPOSITE_UNSAFE_PRIMARY_RATE:      {results['unsafe_primary_rate']:>7.2%}")
    print("-" * 70)
    print(f"1.  Candidate Recall@5:              {results['candidate_recall_at_5']:>7.2%}")
    print(f"2.  Candidate Recall@10:             {results['candidate_recall_at_10']:>7.2%}")
    print(f"3.  MRR (Mean Reciprocal Rank):      {results.get('MRR', 0.0):>7.4f}")
    print(f"4.  In-Scope Primary Accuracy:       {results['in_scope_primary_accuracy']:>7.2%}")
    print(f"5.  Outside-Coverage Accuracy:       {results['outside_coverage_accuracy']:>7.2%}")
    print(f"6.  Safe Decision Contract Accuracy: {results['safe_decision_accuracy']:>7.2%}")
    print(f"7.  Legacy Raw Decision Match:       {results['decision_accuracy_raw']:>7.2%}")
    print(f"8.  Safe Abstention Rate on Unready: {safe_abst_str}")
    print(f"9.  Regulatory Mandate Accuracy:     {results['regulatory_accuracy']:>7.2%}")
    print("-" * 70)
    print(f"10. Hard Negative Rejection (HNRR@1):{results['hnrr_at1']:>7.2%}  ({results['total_hard_negatives']} evaluated)")
    print(f"11. HN Intrusion Rate @ 5:           {results['hn_intrusion_rate_5']:>7.2%}")
    print(f"12. HN Intrusion Rate @ 10:          {results['hn_intrusion_rate_10']:>7.2%}")
    print(f"13. Expected Calibration Error (ECE):{results['ece']:>7.4f}  (Diagnostic on N={results['n_queries']})")
    print(f"    Brier Score (Diagnostic):        {results['brier_score']:>7.4f}")
    print("-" * 70)
    print("--- Per-Query Results ---")
    for r in results["per_query_results"]:
        status = "CORRECT" if r["retrieval_correct"] else ("HIT@K" if r["hit_in_top_k"] else "MISS")
        wp_flag = " [WRONG PRIMARY]" if r.get("wrong_primary") else ""
        top_cand = r["primary_recommendation"] or (f"{r['review_candidate']} (REVIEW)" if r['review_candidate'] else 'NONE')
        print(
            f"  [{r['query_id']}] {status:<8}{wp_flag:<16} | Decision: {r['decision_state']:<28} "
            f"| Top: {top_cand:<35} | Golds: {r['expected_golds']}"
        )
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Evaluate StandSpec AI End-to-End Recommender")
    parser.add_argument("--benchmark", "-b", default="data/benchmarks/val.jsonl")
    parser.add_argument("--graph", "-g", default="data/processed/standards_graph.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output-json", "-o", default=None, help="Save evaluation metrics to JSON file")

    args = parser.parse_args()
    bench_p = Path(args.benchmark)
    graph_p = Path(args.graph)

    if not bench_p.exists() or not graph_p.exists():
        print("Error: benchmark or graph file missing.")
        sys.exit(1)

    print(f"Running End-to-End Evaluation on {bench_p}...")
    report = evaluate_engine_on_benchmark(bench_p, graph_p, top_k=args.top_k)
    print_report(report, bench_p)

    if args.output_json:
        out_p = Path(args.output_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        # Format payload for machine readability
        payload = {
            "benchmark_path": str(bench_p.as_posix()),
            "graph_path": str(graph_p.as_posix()),
            "top_k": args.top_k,
            "metrics": {k: v for k, v in report.items() if k != "per_query_results"},
            "per_query_results": report.get("per_query_results", []),
        }
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"[OK] Machine-readable evaluation saved to {out_p}")


if __name__ == "__main__":
    main()

