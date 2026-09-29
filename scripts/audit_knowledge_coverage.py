"""
Knowledge Coverage Audit and Evidence Acquisition Prioritization — StandSpec AI (Phase P1-E Sections 7 & 8).

Audits:
1. Usable evidence coverage across all 6,081 graph nodes.
2. Gold standard evidentiary availability across benchmarks.
3. Splits misleading 'gold_in_scope' into precise evidentiary states:
   - prototype_coverage_state
   - gold_in_graph
   - gold_primary_candidate_eligible
   - gold_evidence_state
   - gold_recommendation_ready
4. Generates data/reports/knowledge_coverage.json and data/reports/evidence_acquisition_priority.jsonl.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, Any, List, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.recommendation.corpus_policy import CandidateEligibilityPolicy

GRAPH_PATH = PROJECT_ROOT / "data" / "processed" / "standards_graph.json"
BENCHMARK_DIR = PROJECT_ROOT / "data" / "benchmarks"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"


def audit_knowledge_coverage(graph: dict, benchmark_files: List[Path]) -> Dict[str, Any]:
    nodes = graph.get("nodes", [])
    total_nodes = len(nodes)

    # 1. Node role aggregation
    role_buckets = defaultdict(list)
    for n in nodes:
        role = n.get("standard_role", "UNKNOWN_ROLE")
        role_buckets[role].append(n)

    def analyze_bucket(bucket_nodes: List[dict]) -> Dict[str, Any]:
        count = len(bucket_nodes)
        if count == 0:
            return {
                "count": 0,
                "scope_availability": 0,
                "scope_percentage": 0.0,
                "provenance_availability": 0,
                "lifecycle_availability": 0,
                "department_availability": 0,
                "candidate_readiness": 0,
                "hydration_count": 0,
                "regulatory_mapping_count": 0,
            }

        scope_count = sum(1 for n in bucket_nodes if bool((n.get("scope") or "").strip()))
        prov_count = sum(1 for n in bucket_nodes if bool(n.get("source_department") or n.get("publisher")))
        life_count = sum(1 for n in bucket_nodes if bool((n.get("lifecycle") or {}).get("status") or n.get("lifecycle_status")))
        dept_count = sum(1 for n in bucket_nodes if bool(n.get("source_department") in ("CED", "ETD")))
        ready_count = sum(1 for n in bucket_nodes if bool(n.get("recommendation_ready")))
        hydrated_count = sum(1 for n in bucket_nodes if bool(n.get("is_hydrated")))
        reg_count = sum(1 for n in bucket_nodes if bool(n.get("is_mandatory_qco") or n.get("is_mandatory_crs")))

        return {
            "count": count,
            "scope_availability": scope_count,
            "scope_percentage": round(scope_count / count * 100, 2),
            "provenance_availability": prov_count,
            "lifecycle_availability": life_count,
            "department_availability": dept_count,
            "candidate_readiness": ready_count,
            "hydration_count": hydrated_count,
            "regulatory_mapping_count": reg_count,
        }

    role_analysis = {}
    for role, r_nodes in role_buckets.items():
        role_analysis[role] = analyze_bucket(r_nodes)

    # 2. Overall Summary
    total_scope = sum(1 for n in nodes if bool((n.get("scope") or "").strip()))
    total_ready = sum(1 for n in nodes if bool(n.get("recommendation_ready")))
    total_primary_eligible = sum(1 for n in nodes if CandidateEligibilityPolicy.is_primary_candidate(n))

    node_by_desig = {n.get("designation"): n for n in nodes if n.get("designation")}

    # 3. Gold Standard Audit across Benchmarks
    all_golds: Dict[str, Dict[str, Any]] = {}
    benchmark_gold_queries = defaultdict(list)

    for bf in benchmark_files:
        if not bf.exists():
            continue
        with open(bf, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip() or line.strip().startswith("#"):
                    continue
                q = json.loads(line)
                qid = q.get("query_id")
                golds = q.get("gold_standards", [])
                for g in golds:
                    desig = g.get("standard_designation")
                    if desig:
                        benchmark_gold_queries[desig].append({
                            "benchmark": bf.name,
                            "query_id": qid,
                        })

    for desig, query_refs in benchmark_gold_queries.items():
        node = node_by_desig.get(desig)
        in_graph = node is not None
        role = node.get("standard_role", "NOT_IN_GRAPH") if in_graph else "NOT_IN_GRAPH"
        cand_status = node.get("candidate_status", "NOT_IN_GRAPH") if in_graph else "NOT_IN_GRAPH"
        has_scope = bool((node.get("scope") or "").strip()) if in_graph else False
        has_prov = bool(node.get("source_department") or node.get("publisher")) if in_graph else False
        has_life = bool((node.get("lifecycle") or {}).get("status") or node.get("lifecycle_status")) if in_graph else False
        is_primary = CandidateEligibilityPolicy.is_primary_candidate(node) if in_graph else False
        rec_ready = bool(node.get("recommendation_ready")) if in_graph else False

        dept = node.get("source_department") if in_graph else None
        proto_cov = "IN_PROTOTYPE_COVERAGE" if (dept in ("CED", "ETD")) else "OUTSIDE_PROTOTYPE_COVERAGE"

        if in_graph and has_scope and rec_ready:
            ev_state = "COMPLETE"
        elif in_graph and has_scope:
            ev_state = "PARTIAL"
        elif in_graph:
            ev_state = "SCOPE_UNAVAILABLE"
        else:
            ev_state = "ABSENT_FROM_GRAPH"

        all_golds[desig] = {
            "gold_designation": desig,
            "gold_in_graph": in_graph,
            "prototype_coverage_state": proto_cov,
            "role": role,
            "candidate_status": cand_status,
            "scope_available": has_scope,
            "provenance_available": has_prov,
            "lifecycle_available": has_life,
            "gold_primary_candidate_eligible": is_primary,
            "gold_recommendation_ready": rec_ready,
            "gold_evidence_state": ev_state,
            "referenced_in_benchmarks": [r["benchmark"] for r in query_refs],
            "query_count": len(query_refs),
        }

    # 4. Generate Comprehensive Evidence Acquisition Priority Queue
    # Evaluates benchmark golds/HNs AND all unhydrated/scope-empty stubs across the graph
    # Priority scoring factors:
    #   - Benchmark reference (Gold: +50, HN: +30, query count * 5)
    #   - Department (CED / ETD core prototype coverage: +25)
    #   - High-demand procurement category (Cables, Conductors, Transformers, Cement, Steel, Pipes, Motors, Switchgear: +20)
    #   - Role (PRIMARY_PRODUCT: +15, COMPONENT: +5)
    #   - In-degree citation frequency in standards graph (+2 per citation, cap 20)
    
    # Precompute edge in-degrees
    in_degrees = Counter()
    for e in graph.get("edges", []):
        target = e.get("target") or e.get("target_id")
        if target:
            in_degrees[target] += 1

    HIGH_PRIORITY_KEYWORDS = [
        "cable", "conductor", "transformer", "switchgear", "circuit breaker",
        "cement", "concrete", "steel", "pipe", "tube", "motor", "meter",
        "insulat", "aggregate", "sand", "brick", "glass", "door", "window",
    ]

    priority_queue = []
    seen_desigs = set()

    # Pass 1: Benchmark-referenced standards with evidentiary gaps
    for desig, meta in all_golds.items():
        seen_desigs.add(desig)
        if not meta["gold_recommendation_ready"] or not meta["scope_available"]:
            score = 0
            reasons = []
            if not meta["gold_in_graph"]:
                score += 60
                reasons.append("MISSING_FROM_KNOWLEDGE_GRAPH")
            elif not meta["scope_available"]:
                score += 35
                reasons.append("SCOPE_TEXT_EMPTY_IN_KB")

            if "adversarial.jsonl" in meta["referenced_in_benchmarks"]:
                score += 25
                reasons.append("APPEARS_IN_ADVERSARIAL_BENCHMARK")
            if "challenge.jsonl" in meta["referenced_in_benchmarks"]:
                score += 20
                reasons.append("APPEARS_IN_CHALLENGE_BENCHMARK")
            if "test.jsonl" in meta["referenced_in_benchmarks"]:
                score += 15
                reasons.append("APPEARS_IN_CORE_TEST_SPLIT")

            score += meta["query_count"] * 5

            priority_queue.append({
                "standard_designation": desig,
                "priority_score": score,
                "priority_tier": "HIGH" if score >= 40 else ("MEDIUM" if score >= 20 else "LOW"),
                "in_graph": meta["gold_in_graph"],
                "scope_available": meta["scope_available"],
                "department": meta.get("department") or "UNKNOWN",
                "role": meta["role"],
                "candidate_status": meta["candidate_status"],
                "reasons": reasons,
                "benchmark_references": meta["referenced_in_benchmarks"],
            })

    # Pass 2: All unhydrated / scope-empty nodes across the entire knowledge graph
    for n in nodes:
        desig = n.get("designation") or n.get("id") or ""
        if not desig or desig in seen_desigs:
            continue
        has_scope = bool((n.get("scope") or "").strip())
        is_hydrated = bool(n.get("is_hydrated"))
        rec_ready = bool(n.get("recommendation_ready"))

        # We care about nodes that lack scope or are unhydrated stubs
        if not has_scope or not is_hydrated or not rec_ready:
            seen_desigs.add(desig)
            score = 0
            reasons = []

            if not has_scope:
                score += 30
                reasons.append("SCOPE_TEXT_EMPTY_IN_KB")
            elif not is_hydrated:
                score += 15
                reasons.append("UNHYDRATED_METADATA_STUB")

            dept = (n.get("source_department") or n.get("department") or "").upper()
            if dept in ("CED", "ETD"):
                score += 25
                reasons.append(f"CORE_PROTOTYPE_DEPARTMENT_{dept}")

            title = (n.get("title") or "").lower()
            if any(k in title for k in HIGH_PRIORITY_KEYWORDS):
                score += 20
                reasons.append("HIGH_DEMAND_PROCUREMENT_CATEGORY")

            role = n.get("standard_role", "UNKNOWN_ROLE")
            if role == "PRIMARY_PRODUCT":
                score += 15
                reasons.append("PRIMARY_PRODUCT_ROLE")
            elif role == "COMPONENT":
                score += 5

            # Graph connectivity
            citations = in_degrees.get(desig, 0)
            if citations > 0:
                cit_score = min(20, citations * 2)
                score += cit_score
                reasons.append(f"REFERENCED_BY_{citations}_STANDARDS")

            priority_queue.append({
                "standard_designation": desig,
                "priority_score": score,
                "priority_tier": "HIGH" if score >= 45 else ("MEDIUM" if score >= 25 else "LOW"),
                "in_graph": True,
                "scope_available": has_scope,
                "department": dept or "UNKNOWN",
                "role": role,
                "candidate_status": n.get("candidate_status", "UNKNOWN"),
                "reasons": reasons,
                "benchmark_references": [],
            })

    priority_queue.sort(key=lambda x: x["priority_score"], reverse=True)

    report = {
        "audit_timestamp": "2026-09-29T12:00:00Z",
        "total_nodes": total_nodes,
        "total_scope_bearing_nodes": total_scope,
        "total_recommendation_ready_nodes": total_ready,
        "total_primary_candidate_eligible_nodes": total_primary_eligible,
        "usable_scope_coverage_percentage": round(total_scope / total_nodes * 100, 2),
        "usable_readiness_percentage": round(total_ready / total_nodes * 100, 2),
        "roles_breakdown": role_analysis,
        "benchmark_golds_audit": {
            "total_golds_evaluated": len(all_golds),
            "golds_in_graph": sum(1 for g in all_golds.values() if g["gold_in_graph"]),
            "golds_with_scope": sum(1 for g in all_golds.values() if g["scope_available"]),
            "golds_recommendation_ready": sum(1 for g in all_golds.values() if g["gold_recommendation_ready"]),
            "golds_by_evidence_state": dict(Counter(g["gold_evidence_state"] for g in all_golds.values())),
            "details": all_golds,
        },
        "acquisition_queue_summary": {
            "total_standards_in_queue": len(priority_queue),
            "high_priority_count": sum(1 for p in priority_queue if p["priority_tier"] == "HIGH"),
            "medium_priority_count": sum(1 for p in priority_queue if p["priority_tier"] == "MEDIUM"),
        }
    }

    return report, priority_queue


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    benchmarks = [
        BENCHMARK_DIR / "test.jsonl",
        BENCHMARK_DIR / "val.jsonl",
        BENCHMARK_DIR / "adversarial.jsonl",
        BENCHMARK_DIR / "challenge.jsonl",
        BENCHMARK_DIR / "coverage_boundary.jsonl",
    ]

    report, priority_queue = audit_knowledge_coverage(graph, benchmarks)

    cov_file = REPORTS_DIR / "knowledge_coverage.json"
    with open(cov_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    queue_file = REPORTS_DIR / "evidence_acquisition_priority.jsonl"
    with open(queue_file, "w", encoding="utf-8") as f:
        for item in priority_queue:
            f.write(json.dumps(item) + "\n")

    print(f"[OK] Knowledge coverage audit written to: {cov_file}")
    print(f"[OK] Evidence acquisition queue written to: {queue_file}")
    print(f"Total nodes: {report['total_nodes']}")
    print(f"Scope-bearing nodes: {report['total_scope_bearing_nodes']} ({report['usable_scope_coverage_percentage']}%)")
    print(f"Recommendation-ready nodes: {report['total_recommendation_ready_nodes']} ({report['usable_readiness_percentage']}%)")
    print(f"Benchmark golds audited: {report['benchmark_golds_audit']['total_golds_evaluated']}")
    print(f"Golds with scope: {report['benchmark_golds_audit']['golds_with_scope']} / {report['benchmark_golds_audit']['total_golds_evaluated']}")
    print(f"Top 5 evidence acquisition targets:")
    for p in priority_queue[:5]:
        print(f"  [{p['priority_tier']}] {p['standard_designation']} (Score: {p['priority_score']}) -> {p['reasons']}")


if __name__ == "__main__":
    main()
