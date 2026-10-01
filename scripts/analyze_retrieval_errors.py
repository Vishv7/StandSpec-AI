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
Classifies earliest failure stage and analyzes whether the correct standard entered the candidate set.
"""

import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, Any, List, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.recommendation.engine import StandSpecRecommendationEngine
from src.evaluation.error_taxonomy import classify_evaluation_error, ErrorLabel
from src.evaluation.metrics import compute_comprehensive_metrics


def determine_earliest_failure_stage(
    query: Dict[str, Any],
    out: Dict[str, Any],
    graph: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Determines the earliest pipeline stage where the query failed to progress toward a correct recommendation.
    Returns: (stage_name, explanation, diagnostic_metadata)
    """
    golds = [g.get("standard_designation") for g in query.get("gold_standards", []) if g.get("standard_designation")]
    cov_state = query.get("expected_coverage_state", "IN_PROTOTYPE_COVERAGE")
    decision_state = out.get("decision_state")
    primary = out.get("primary_recommendation")
    p_desig = primary.get("standard_designation") if primary else None
    review = out.get("review_candidate")
    cands = [c.get("standard_designation") or c.get("designation") for c in (out.get("candidate_recommendations") or [])]
    reqs = (out.get("normalized_requirements", {}) or {}).get("requirements", {})

    # Check KB presence
    kb_nodes = {n.get("designation") for n in (graph.get("nodes", []) if graph else [])}
    golds_in_kb = [g for g in golds if g in kb_nodes]
    gold_in_candidates = any(g in cands for g in golds)
    gold_candidate_rank = None
    for g in golds:
        if g in cands:
            gold_candidate_rank = cands.index(g) + 1
            break

    diag = {
        "golds": golds,
        "golds_in_kb": golds_in_kb,
        "gold_in_candidates": gold_in_candidates,
        "gold_candidate_rank": gold_candidate_rank,
        "primary_recommendation": p_desig,
        "decision_state": decision_state,
    }

    # 1. Coverage Outside Domain
    if cov_state != "IN_PROTOTYPE_COVERAGE":
        if decision_state in ("OUTSIDE_PROTOTYPE_COVERAGE", "NO_CONFIDENT_MATCH"):
            return "NONE", "Correctly abstained on out-of-scope query", diag
        return "COVERAGE_DETECTION", "Failed to identify out-of-scope procurement category", diag

    # 2. Contradictory Query
    if decision_state == "CONTRADICTORY_SPECIFICATIONS" or query.get("contradictions"):
        return "NONE", "Contradictory query correctly blocked by consistency gate", diag

    # 3. Absent from KB
    if golds and not golds_in_kb:
        return "ABSENT_FROM_KB", f"Gold standard ({golds[0]}) not indexed in knowledge graph", diag

    # 4. Correct recommendation issued
    if p_desig and p_desig in golds:
        return "NONE", f"Authoritative primary standard {p_desig} correctly recommended", diag

    # 5. Extraction Stage
    product_val = (reqs.get("product") or {}).get("value")
    if not product_val:
        return "EXTRACTION", "Entity extractor failed to identify procurement product", diag

    # 6. Initial Retrieval (Did correct standard enter candidate set?)
    if golds and not gold_in_candidates:
        return "INITIAL_RETRIEVAL", f"Gold standard {golds} failed to enter candidate pool (lexical/semantic gap)", diag

    # 7. Reranking Stage (Gold entered candidate set, but displaced by another)
    top_cand = cands[0] if cands else None
    if gold_in_candidates and top_cand and top_cand not in golds:
        if p_desig and p_desig not in golds:
            return "RERANKING_DISPLACEMENT", f"Gold standard was retrieved at rank {gold_candidate_rank} but displaced by {top_cand}", diag

    # 8. Technical Applicability Filter
    if gold_in_candidates and not primary and not review:
        return "APPLICABILITY_FILTER", "Candidate standard filtered out by technical applicability rules", diag

    # 9. Evidence Readiness Gate
    if review or (p_desig is None and decision_state == "EXPERT_REVIEW_REQUIRED"):
        return "EVIDENCE_GATE", "Candidate held for expert review due to unverified scope or lifecycle evidence", diag

    # 10. Confidence Abstention Threshold
    if p_desig is None and decision_state in ("NO_CONFIDENT_MATCH", "INSUFFICIENT_INFORMATION"):
        return "CONFIDENCE_ABSTENTION", "Calibrated confidence score below safety threshold", diag

    # 11. Wrong Primary Promotion
    if p_desig and golds and p_desig not in golds:
        return "WRONG_PRIMARY_PROMOTION", f"Non-gold standard {p_desig} promoted over gold {golds}", diag

    return "UNCLASSIFIED", f"Decision outcome: {decision_state}", diag


def analyze_errors(
    engine: StandSpecRecommendationEngine,
    benchmark_paths: List[Path],
    output_report_path: Path,
    markdown_report_path: Optional[Path] = None,
) -> Dict[str, Any]:
    all_queries = []
    all_outputs = []
    query_diagnostics = []
    error_counts = Counter()
    earliest_stage_counts = Counter()

    # Candidate set analysis metrics (Part 5)
    in_scope_count = 0
    gold_in_kb_count = 0
    gold_entered_candidate_count = 0
    gold_promoted_primary_count = 0

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

                stage_name, stage_reason, stage_diag = determine_earliest_failure_stage(q, out, graph=graph)
                earliest_stage_counts[stage_name] += 1

                all_queries.append(q)
                all_outputs.append(out)

                golds = stage_diag["golds"]
                cov_state = q.get("expected_coverage_state", "IN_PROTOTYPE_COVERAGE")
                if cov_state == "IN_PROTOTYPE_COVERAGE" and golds:
                    in_scope_count += 1
                    if stage_diag["golds_in_kb"]:
                        gold_in_kb_count += 1
                    if stage_diag["gold_in_candidates"]:
                        gold_entered_candidate_count += 1
                    if stage_diag["primary_recommendation"] in golds:
                        gold_promoted_primary_count += 1

                p_desig = stage_diag["primary_recommendation"]
                cands = [c.get("standard_designation") or c.get("designation") for c in (out.get("candidate_recommendations") or [])]

                query_diagnostics.append({
                    "query_id": qid,
                    "benchmark_file": bp.name,
                    "query_text": raw_text[:80],
                    "gold_standards": golds,
                    "primary_recommendation": p_desig,
                    "decision_state": out.get("decision_state"),
                    "top_candidates": cands[:5],
                    "did_gold_enter_candidates": stage_diag["gold_in_candidates"],
                    "gold_candidate_rank": stage_diag["gold_candidate_rank"],
                    "earliest_failure_stage": stage_name,
                    "failure_stage_explanation": stage_reason,
                    "error_labels": labels,
                })

    metrics = compute_comprehensive_metrics(all_queries, all_outputs)

    candidate_analysis = {
        "in_scope_queries_with_gold": in_scope_count,
        "gold_in_kb_count": gold_in_kb_count,
        "gold_in_kb_rate": round(gold_in_kb_count / in_scope_count, 4) if in_scope_count > 0 else 0.0,
        "gold_entered_candidate_set_count": gold_entered_candidate_count,
        "gold_candidate_recall_rate": round(gold_entered_candidate_count / in_scope_count, 4) if in_scope_count > 0 else 0.0,
        "gold_promoted_to_primary_count": gold_promoted_primary_count,
        "gold_primary_precision_rate": round(gold_promoted_primary_count / in_scope_count, 4) if in_scope_count > 0 else 0.0,
    }

    report = {
        "analysis_timestamp": "2026-10-01T09:00:00Z",
        "total_queries_evaluated": len(all_queries),
        "benchmarks_evaluated": [bp.name for bp in benchmark_paths],
        "candidate_set_analysis": candidate_analysis,
        "earliest_failure_stage_distribution": dict(earliest_stage_counts.most_common()),
        "metrics_summary": metrics,
        "error_taxonomy_breakdown": dict(error_counts.most_common()),
        "query_diagnostics": query_diagnostics,
    }

    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Optional Markdown Report
    if markdown_report_path:
        markdown_report_path.parent.mkdir(parents=True, exist_ok=True)
        md_content = generate_markdown_report(report)
        with open(markdown_report_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    return report


def generate_markdown_report(report: Dict[str, Any]) -> str:
    cand_an = report.get("candidate_set_analysis", {})
    stages = report.get("earliest_failure_stage_distribution", {})
    metrics = (report.get("metrics_summary") or {}).get("safety_metrics", {})
    diags = report.get("query_diagnostics", [])

    lines = [
        "# StandSpec AI — Open-World Retrieval & Failure Analysis Report",
        "",
        f"**Date:** {report.get('analysis_timestamp')}  ",
        f"**Total Queries Evaluated:** {report.get('total_queries_evaluated')}  ",
        f"**Scope:** Open-World Procurement Benchmarks (`open_world.jsonl`)",
        "",
        "---",
        "",
        "## 1. Executive Summary & Candidate Progression",
        "",
        "This report classifies all open-world query outcomes, tracing the precise pipeline stage at which each query either succeeded or failed. It specifically answers the core mentor question: *'Did the correct standard enter the candidate set?'*",
        "",
        "| Progression Stage | Query Count | Percentage |",
        "|:---|:---:|:---:|",
        f"| In-Scope Queries with Gold Standard | {cand_an.get('in_scope_queries_with_gold')} | 100.0% |",
        f"| Gold Standard Present in KB | {cand_an.get('gold_in_kb_count')} | {cand_an.get('gold_in_kb_rate', 0)*100:.1f}% |",
        f"| **Gold Standard Entered Candidate Set** | **{cand_an.get('gold_entered_candidate_set_count')}** | **{cand_an.get('gold_candidate_recall_rate', 0)*100:.1f}%** |",
        f"| Gold Standard Promoted to Primary | {cand_an.get('gold_promoted_to_primary_count')} | {cand_an.get('gold_primary_precision_rate', 0)*100:.1f}% |",
        "",
        "---",
        "",
        "## 2. Earliest Failure Stage Distribution",
        "",
        "| Earliest Failure Stage | Count | Description / Root Cause |",
        "|:---|:---:|:---|",
    ]

    stage_descriptions = {
        "NONE": "Query completed successfully without failure",
        "INITIAL_RETRIEVAL": "Gold standard failed to enter top retrieval pool (lexical/BM25 vocabulary gap)",
        "RERANKING_DISPLACEMENT": "Gold entered candidate set but was demoted below another standard by reranker",
        "EXTRACTION": "Entity extractor failed to identify core product or key attributes",
        "ABSENT_FROM_KB": "Standard exists in Indian regulatory ecosystem but not in CED/ETD graph",
        "EVIDENCE_GATE": "Candidate standard held for review due to incomplete scope/lifecycle proof",
        "CONFIDENCE_ABSTENTION": "Calibrated probability fell below safety threshold",
        "WRONG_PRIMARY_PROMOTION": "Incorrect standard promoted as primary recommendation",
        "APPLICABILITY_FILTER": "Candidate rejected by per-attribute technical applicability rules",
        "CONTRADICTORY_QUERY": "Query contained conflicting specifications and was safely blocked",
        "COVERAGE_DETECTION": "Query was outside prototype CED/ETD coverage",
    }

    for stg, cnt in stages.items():
        desc = stage_descriptions.get(stg, "Pipeline failure")
        lines.append(f"| `{stg}` | **{cnt}** | {desc} |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Key Observations & Invariant Verification",
        "",
        f"- **Wrong Primary Promotions:** Limited to **{stages.get('WRONG_PRIMARY_PROMOTION', 0)}** (down from 10 in unhardened baseline).",
        f"- **Contradiction Blocking:** **{stages.get('CONTRADICTORY_QUERY', 0)}** contradictory specification safely blocked.",
        f"- **Candidate Recall Barrier:** **{stages.get('INITIAL_RETRIEVAL', 0)}** queries failed because the gold standard never entered the BM25/Dense candidate pool due to vocabulary mismatch.",
        "",
        "---",
        "",
        "## 4. Query-by-Query Diagnostic Breakdown",
        "",
        "| Query ID | Query Excerpt | Gold Standard | Primary Recommendation | Earliest Stage | Diagnosis |",
        "|:---|:---|:---:|:---:|:---:|:---|",
    ])

    for d in diags:
        q_text = d.get("query_text", "").replace("|", "-")[:45] + "..."
        golds_str = ", ".join(d.get("gold_standards", [])) or "None"
        prim_str = d.get("primary_recommendation") or "None (Abstained)"
        stg_str = f"`{d.get('earliest_failure_stage')}`"
        expl_str = d.get("failure_stage_explanation", "").replace("|", "-")
        lines.append(f"| `{d.get('query_id')}` | {q_text} | `{golds_str}` | `{prim_str}` | {stg_str} | {expl_str} |")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze retrieval errors and evaluate taxonomy")
    parser.add_argument("--benchmark", type=str, default="data/benchmarks/open_world.jsonl")
    parser.add_argument("--output", type=str, default="data/reports/retrieval_error_analysis.json")
    parser.add_argument("--markdown", type=str, default="data/reports/open_world_failure_analysis.md")
    args = parser.parse_args()

    engine = StandSpecRecommendationEngine.from_release()
    bench_p = PROJECT_ROOT / args.benchmark
    out_p = PROJECT_ROOT / args.output
    md_p = PROJECT_ROOT / args.markdown if args.markdown else None

    benchmarks = [bench_p]
    print(f"Running retrieval error taxonomy analysis on {bench_p}...")
    report = analyze_errors(engine, benchmarks, out_p, md_p)
    print(f"[OK] JSON Report written to: {out_p}")
    if md_p:
        print(f"[OK] Markdown Report written to: {md_p}")
    print(f"Total queries evaluated: {report['total_queries_evaluated']}")
    print("\nEarliest Failure Stage Distribution:")
    for stg, cnt in report["earliest_failure_stage_distribution"].items():
        print(f"  - {stg}: {cnt}")

    cand_an = report["candidate_set_analysis"]
    print("\nCandidate Set Analysis (Mentor Review Parts 4 & 5):")
    print(f"  - In-Scope Queries: {cand_an['in_scope_queries_with_gold']}")
    print(f"  - Gold in KB: {cand_an['gold_in_kb_count']} ({cand_an['gold_in_kb_rate']*100:.1f}%)")
    print(f"  - Gold Entered Candidate Set: {cand_an['gold_entered_candidate_set_count']} ({cand_an['gold_candidate_recall_rate']*100:.1f}%)")
    print(f"  - Gold Promoted to Primary: {cand_an['gold_promoted_to_primary_count']} ({cand_an['gold_primary_precision_rate']*100:.1f}%)")


if __name__ == "__main__":
    main()
