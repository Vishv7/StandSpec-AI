import json
import sys
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.recommendation.engine import StandSpecRecommendationEngine
from src.evaluation.metrics import (
    is_primary_unsupported,
    is_primary_wrong_role,
    is_primary_wrong_edition,
    compute_safety_metrics,
)

graph_path = PROJECT_ROOT / "data" / "processed" / "standards_graph.json"
bench_path = PROJECT_ROOT / "data" / "benchmarks" / "test.jsonl"

with open(graph_path, "r", encoding="utf-8") as f:
    graph = json.load(f)

engine = StandSpecRecommendationEngine(graph)

queries = []
with open(bench_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            queries.append(json.loads(line))

diagnostic_cases = []

for q in queries:
    qid = q.get("query_id")
    raw_text = q.get("query", {}).get("raw_text", "")
    eval_date = q.get("source", {}).get("evaluation_as_of_date")
    golds = [g.get("standard_designation") for g in q.get("gold_standards", [])]
    cov_state = q.get("prototype_coverage_state") or q.get("expected_coverage_state", "IN_PROTOTYPE_COVERAGE")
    hns = [h.get("standard_designation") for h in q.get("hard_negatives", [])]
    
    out = engine.recommend(raw_text, evaluation_date=eval_date, top_k=5)
    
    primary = out.get("primary_recommendation")
    review = out.get("review_candidate")
    decision_state = out.get("decision_state")
    claim_level = out.get("claim_level")
    abstention_reason = out.get("abstention_reason")
    
    if primary:
        desig = primary.get("standard_designation")
        is_wrong = (cov_state == "IN_PROTOTYPE_COVERAGE" and len(golds) > 0 and desig not in golds)
        unsupported = is_primary_unsupported(primary)
        wrong_role = is_primary_wrong_role(primary)
        wrong_edition = is_primary_wrong_edition(primary)
        in_hns = desig in hns
        
        is_unsafe = is_wrong or unsupported or wrong_role or wrong_edition or in_hns
        
        bundle = primary.get("evidence_bundle") or {}
        lifecycle = primary.get("lifecycle") or {}
        regulatory = primary.get("regulatory") or {}
        applicability = primary.get("applicability") or {}
        
        # Determine exact decision stage that allowed promotion:
        # Trace decision_trace
        decision_trace = out.get("decision_trace", [])
        
        case_info = {
            "query_id": qid,
            "query_text": raw_text,
            "expected_golds": golds,
            "returned_primary": desig,
            "returned_decision_state": decision_state,
            "candidate_applicability": applicability.get("state") or primary.get("applicability_state"),
            "candidate_role": bundle.get("standard_role") or primary.get("standard_role"),
            "evidence_readiness": {
                "recommendation_ready": primary.get("recommendation_ready"),
                "scope_ready": bundle.get("scope_ready"),
                "applicability_ready": bundle.get("applicability_ready"),
                "lifecycle_ready": bundle.get("lifecycle_ready"),
                "provenance_ready": bundle.get("provenance_ready"),
                "evidence_gaps": primary.get("evidence_gaps") or bundle.get("evidence_gaps", []),
            },
            "lifecycle_readiness": {
                "lifecycle_state": lifecycle.get("lifecycle_state") or lifecycle.get("status"),
                "is_superseded": lifecycle.get("is_superseded"),
                "recommended_edition": lifecycle.get("recommended_edition"),
            },
            "regulatory_readiness": {
                "regulatory_state": regulatory.get("regulatory_state"),
                "mandate_type": regulatory.get("mandate_type"),
            },
            "claim_level": claim_level or primary.get("claim_level"),
            "why_considered_unsafe": {
                "is_wrong_primary": is_wrong,
                "is_unsupported": unsupported,
                "is_wrong_role": wrong_role,
                "is_wrong_edition": wrong_edition,
                "is_in_hard_negatives": in_hns,
            },
            "decision_stage_allowing_promotion": "Step 9 (SelectiveAbstentionPolicy.decide returned top1 despite non-primary state)",
            "abstention_reason": abstention_reason,
            "decision_trace_summary": [
                f"{t.get('stage')}: status={t.get('status')}, blocking={t.get('blocking')}"
                for t in decision_trace
            ]
        }
        if is_unsafe:
            diagnostic_cases.append(case_info)

output_path = PROJECT_ROOT / "data" / "reports" / "unsafe_primary_promotion_diagnostic.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump({
        "total_test_queries": len(queries),
        "total_unsafe_cases": len(diagnostic_cases),
        "unsafe_rate": len(diagnostic_cases) / len(queries),
        "cases": diagnostic_cases
    }, f, indent=2)

print(f"Generated diagnostic report at {output_path}")
print(f"Found {len(diagnostic_cases)} unsafe cases out of {len(queries)} queries ({len(diagnostic_cases)/len(queries):.4f})")
