"""
Benchmark Validator CLI — StandSpec AI (Layer 4)
Validates benchmark JSONL files against schemas/procurement_ground_truth.schema.json,
checks 5 orthogonal dimension distributions, HN1-HN8 coverage, and enforces
zero-leakage split policies across 7 orthogonal dimensions per BENCHMARK_SPLIT_POLICY.md.

Usage:
    python scripts/validate_benchmark.py --input data/benchmarks/procurement_benchmark_template.jsonl
    python scripts/validate_benchmark.py --input data/benchmarks/dataset_a.jsonl --strict
    python scripts/validate_benchmark.py --leakage-check --train data/benchmarks/dataset_b.jsonl --test data/benchmarks/dataset_d.jsonl
"""

import sys
import re
import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
SCHEMA_PATH = SCHEMAS_DIR / "procurement_ground_truth.schema.json"


def load_schema() -> dict:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)
    return schema


def extract_base_standard(designation: str) -> str:
    """Extract base standard identifier (e.g. 'IS 7098 (Part 2):2011' -> 'IS 7098')."""
    d = designation.strip()
    if ":" in d:
        d = d.split(":")[0].strip()
    if "(" in d:
        d = d.split("(")[0].strip()
    return d


def tokenize_query(text: str) -> set[str]:
    """Tokenize query text for near-duplicate Jaccard similarity detection."""
    stopwords = {
        "the", "a", "an", "for", "and", "or", "in", "on", "at", "to", "of",
        "with", "as", "by", "is", "are", "this", "that", "these", "those"
    }
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return {w for w in cleaned.split() if len(w) > 2 and w not in stopwords}


def build_graph_adjacency(graph_path: Path) -> dict[str, set[str]]:
    """Build undirected adjacency map from standards knowledge graph for neighborhood checks."""
    if not graph_path or not graph_path.exists():
        return {}
    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            graph = json.load(f)
        adj = defaultdict(set)
        for e in graph.get("edges", []):
            s = e.get("source")
            t = e.get("target")
            if s and t:
                adj[s].add(t)
                adj[t].add(s)
        return adj
    except Exception:
        return {}


def get_k_hop_neighborhood(start_nodes: set[str], adj: dict[str, set[str]], k: int = 2) -> set[str]:
    """Compute k-hop graph neighborhood for a set of seed nodes."""
    current = set(start_nodes)
    visited = set(start_nodes)
    for _ in range(k):
        next_hop = set()
        for node in current:
            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    next_hop.add(neighbor)
                    visited.add(neighbor)
        current = next_hop
    return visited


def validate_file(file_path: Path, schema: dict, strict: bool = False, strict_isolation: bool = False) -> tuple[bool, dict]:
    """Validate a benchmark JSONL file against schema, distributional rules, and maturity tiers."""
    validator = Draft202012Validator(schema)
    
    records = []
    errors = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {line_num}: JSON decode error: {e}")
                continue
                
            rec_errors = list(validator.iter_errors(rec))
            if rec_errors:
                for err in rec_errors:
                    qid = rec.get("query_id", f"line_{line_num}")
                    errors.append(f"[{qid}] {err.message} at '{'/'.join(str(p) for p in err.path)}'")
            else:
                records.append(rec)

    total_records = len(records)
    metrics = {
        "total_records": total_records,
        "valid_count": total_records,
        "error_count": len(errors),
        "errors": errors,
        "explicitness": Counter(),
        "difficulty": Counter(),
        "language": Counter(),
        "temporal": Counter(),
        "ambiguity": Counter(),
        "hn_classes": Counter(),
        "domains": Counter(),
        "gold_standards_count": 0,
        "hard_negatives_count": 0,
    }

    if not records:
        return len(errors) == 0, metrics

    for rec in records:
        dims = rec.get("benchmark_dimensions", {})
        metrics["explicitness"][dims.get("query_explicitness", "unknown")] += 1
        metrics["difficulty"][dims.get("difficulty", "unknown")] += 1
        metrics["language"][dims.get("language", "unknown")] += 1
        metrics["temporal"][dims.get("temporal_context", "unknown")] += 1
        metrics["ambiguity"][dims.get("ambiguity_class", "unknown")] += 1
        metrics["domains"][rec.get("query", {}).get("domain", "unknown")] += 1

        gold_list = rec.get("gold_standards", [])
        metrics["gold_standards_count"] += len(gold_list)

        hns = rec.get("hard_negatives", [])
        metrics["hard_negatives_count"] += len(hns)
        for hn in hns:
            metrics["hn_classes"][hn.get("hn_class", "unknown")] += 1

    # Distributional checks
    distribution_warnings = []
    if total_records >= 20:
        implicit_ratio = metrics["explicitness"].get("implicit", 0) / total_records
        if implicit_ratio < 0.40 and strict:
            distribution_warnings.append(
                f"Implicit queries ratio is {implicit_ratio:.1%} (target >= 50-60% per specification)"
            )
        
        # Check HN coverage
        present_hn = set(metrics["hn_classes"].keys())
        expected_hn = {f"HN{i}" for i in range(1, 9)}
        missing_hn = expected_hn - present_hn
        if missing_hn and strict:
            distribution_warnings.append(f"Missing hard negative classes: {sorted(missing_hn)}")

    # Strict isolation check: ensure implicit queries do not directly leak target standard designations
    lexical_leakage = []
    if strict_isolation:
        for rec in records:
            qid = rec.get("query_id", "unknown")
            dims = rec.get("benchmark_dimensions", {})
            if dims.get("query_explicitness") == "implicit":
                raw_text = rec.get("query", {}).get("raw_text", "").lower()
                for g in rec.get("gold_standards", []):
                    desig = g.get("standard_designation", "")
                    base = extract_base_standard(desig).lower()
                    if re.search(r'\b' + re.escape(base) + r'\b', raw_text):
                        leak_msg = f"[{qid}] Lexical leakage: Implicit query mentions target '{base}' verbatim"
                        lexical_leakage.append(leak_msg)
                        errors.append(leak_msg)

    # Benchmark Maturity Tier classification
    if len(errors) > 0:
        maturity_tier = "TIER_0_INVALID"
    elif total_records < 4 or metrics["gold_standards_count"] == 0:
        maturity_tier = "TIER_1_SCHEMA_VALID"
    elif total_records < 20 or len(metrics["hn_classes"]) < 6:
        maturity_tier = "TIER_2_PROTOTYPE_TEMPLATE_VALID"
    else:
        maturity_tier = "TIER_3_EVALUATION_READY"

    metrics["maturity_tier"] = maturity_tier
    metrics["lexical_leakage_count"] = len(lexical_leakage)
    metrics["warnings"] = distribution_warnings
    hard_fail = strict or strict_isolation
    success = (len(errors) == 0) and (not hard_fail or len(distribution_warnings) == 0)
    return success, metrics


def check_leakage(train_path: Path, test_path: Path, graph_path: Path = None, temporal_split: bool = False) -> tuple[bool, dict]:
    """
    Check for benchmark split leakage across 7 orthogonal dimensions per BENCHMARK_SPLIT_POLICY.md:
    1. Exact standard ID overlap between train and test.
    2. Base standard family overlap (e.g. IS 7098 Part 1 vs IS 7098 Part 2).
    3. Product family / category overlap.
    4. Procuring organization overlap.
    5. Temporal context / date violations.
    6. Query text near-duplicate detection via token Jaccard similarity (> 0.75).
    7. Graph neighborhood leakage via 2-hop graph cluster Jaccard overlap (> 0.50).
    8. Hard negative overlap (test hard negatives appearing as train gold standards).
    """
    train_queries = []
    train_standards = set()
    train_base_standards = set()
    train_products = set()
    train_org_products = set()
    train_tokens = {}
    train_eval_dates = []

    with open(train_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            rec = json.loads(line)
            qid = rec.get("query_id")
            train_queries.append(rec)

            eval_date = rec.get("source", {}).get("evaluation_as_of_date")
            if eval_date:
                train_eval_dates.append((qid, eval_date))
            
            raw_text = rec.get("query", {}).get("raw_text", "")
            train_tokens[qid] = tokenize_query(raw_text)

            domain = rec.get("query", {}).get("domain") or rec.get("query", {}).get("product_family")
            if domain:
                train_products.add(domain.lower())

            org = rec.get("query", {}).get("procuring_agency") or rec.get("query", {}).get("organization")
            if org and domain:
                train_org_products.add((org.lower(), domain.lower()))

            for g in rec.get("gold_standards", []):
                std = g.get("standard_designation")
                if std:
                    train_standards.add(std)
                    train_base_standards.add(extract_base_standard(std))

    # Graph adjacency for neighborhood checks
    adj = build_graph_adjacency(graph_path) if graph_path else {}

    test_queries = []
    leakage_exact = []
    leakage_family = []
    leakage_product = []
    leakage_org = []
    leakage_near_duplicates = []
    leakage_graph_neighborhood = []
    leakage_hard_negatives = []
    test_eval_dates = []

    with open(test_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            rec = json.loads(line)
            test_queries.append(rec)
            qid = rec.get("query_id")
            raw_text = rec.get("query", {}).get("raw_text", "")
            test_tok = tokenize_query(raw_text)

            # Check 1 & 2: Exact & Base Standard Overlap
            test_golds = set()
            for g in rec.get("gold_standards", []):
                std = g.get("standard_designation")
                if std:
                    test_golds.add(std)
                    base = extract_base_standard(std)
                    if std in train_standards:
                        leakage_exact.append((qid, std))
                    elif base in train_base_standards:
                        leakage_family.append((qid, std, base))

            # Check 3: Product family overlap
            domain = rec.get("query", {}).get("domain") or rec.get("query", {}).get("product_family")
            if domain and domain.lower() in train_products:
                leakage_product.append((qid, domain))

            # Check 4: Organization overlap
            org = rec.get("query", {}).get("procuring_agency") or rec.get("query", {}).get("organization")
            if org and domain and (org.lower(), domain.lower()) in train_org_products:
                leakage_org.append((qid, org, domain))

            # Check 5: Near-duplicate query text (Jaccard > 0.75)
            for t_qid, t_tok in train_tokens.items():
                if test_tok and t_tok:
                    jaccard = len(test_tok.intersection(t_tok)) / len(test_tok.union(t_tok))
                    if jaccard > 0.75:
                        leakage_near_duplicates.append((qid, t_qid, round(jaccard, 3)))

            # Check 6: Graph neighborhood leakage (Jaccard > 0.50 on 2-hop graph clusters)
            if adj and test_golds:
                test_neighborhood = get_k_hop_neighborhood(test_golds, adj, k=2)
                for tr_q in train_queries:
                    tr_qid = tr_q.get("query_id")
                    tr_golds = {g.get("standard_designation") for g in tr_q.get("gold_standards", []) if g.get("standard_designation")}
                    if tr_golds:
                        tr_neighborhood = get_k_hop_neighborhood(tr_golds, adj, k=2)
                        if test_neighborhood and tr_neighborhood:
                            graph_jaccard = len(test_neighborhood.intersection(tr_neighborhood)) / len(test_neighborhood.union(tr_neighborhood))
                            if graph_jaccard > 0.50:
                                leakage_graph_neighborhood.append((qid, tr_qid, round(graph_jaccard, 3)))

            # Check 7: Hard negative overlap (test hard negatives cannot be train gold standards)
            for hn in rec.get("hard_negatives", []):
                hn_std = hn.get("standard_designation")
                if hn_std and hn_std in train_standards:
                    leakage_hard_negatives.append((qid, hn_std))

            test_eval_date = rec.get("source", {}).get("evaluation_as_of_date")
            if test_eval_date:
                test_eval_dates.append((qid, test_eval_date))

    # Check 8 (temporal): train records must not be newer than test records
    temporal_violations = []
    if temporal_split:
        if not train_eval_dates or not test_eval_dates:
            temporal_violations.append(
                f"temporal_split requested but missing evaluation_as_of_date "
                f"(train: {len(train_eval_dates)}, test: {len(test_eval_dates)})"
            )
        else:
            max_train_date = max(d for _, d in train_eval_dates)
            min_test_date = min(d for _, d in test_eval_dates)
            if max_train_date > min_test_date:
                temporal_violations.append(
                    f"Temporal leakage: max(train evaluation_as_of_date={max_train_date}) "
                    f"exceeds min(test evaluation_as_of_date={min_test_date})"
                )

    leakage_clean = (
        len(leakage_exact) == 0
        and len(leakage_family) == 0
        and len(leakage_near_duplicates) == 0
        and len(leakage_graph_neighborhood) == 0
        and len(leakage_hard_negatives) == 0
        and len(temporal_violations) == 0
    )

    report = {
        "train_queries_count": len(train_queries),
        "test_queries_count": len(test_queries),
        "train_standards_count": len(train_standards),
        "train_base_count": len(train_base_standards),
        "leakage_exact_count": len(leakage_exact),
        "leakage_family_count": len(leakage_family),
        "leakage_product_count": len(leakage_product),
        "leakage_org_count": len(leakage_org),
        "leakage_near_duplicates_count": len(leakage_near_duplicates),
        "leakage_graph_neighborhood_count": len(leakage_graph_neighborhood),
        "leakage_hard_negatives_count": len(leakage_hard_negatives),
        "leakage_exact_instances": leakage_exact[:10],
        "leakage_family_instances": leakage_family[:10],
        "leakage_product_instances": leakage_product[:10],
        "leakage_org_instances": leakage_org[:10],
        "leakage_near_duplicates_instances": leakage_near_duplicates[:10],
        "leakage_graph_neighborhood_instances": leakage_graph_neighborhood[:10],
        "leakage_hard_negatives_instances": leakage_hard_negatives[:10],
        "temporal_violations": temporal_violations,
        "temporal_violations_count": len(temporal_violations),
        "max_train_eval_date": max((d for _, d in train_eval_dates), default=None),
        "min_test_eval_date": min((d for _, d in test_eval_dates), default=None),
    }
    return leakage_clean, report


def print_report(filepath: Path, success: bool, metrics: dict):
    print("=" * 70)
    print(f"StandSpec AI — Benchmark Validation Report")
    print(f"Target: {filepath}")
    print(f"Verdict: {'PASS' if success else 'FAIL'}")
    print(f"Benchmark Maturity Tier: {metrics.get('maturity_tier', 'UNKNOWN')}")
    print("=" * 70)
    print(f"Total Queries: {metrics['total_records']}")
    print(f"Schema Errors: {metrics['error_count']}")
    print(f"Gold Standards: {metrics['gold_standards_count']}")
    print(f"Hard Negatives: {metrics['hard_negatives_count']}")
    print()

    print("--- 5 Orthogonal Dimensions Distribution ---")
    print(f"Explicitness:  {dict(metrics['explicitness'])}")
    print(f"Difficulty:    {dict(metrics['difficulty'])}")
    print(f"Language:      {dict(metrics['language'])}")
    print(f"Temporal:      {dict(metrics['temporal'])}")
    print(f"Ambiguity:     {dict(metrics['ambiguity'])}")
    print()

    print("--- Hard Negative Classes (HN1-HN8) ---")
    print(f"HN Distribution: {dict(metrics['hn_classes'])}")
    print()

    if metrics.get("warnings"):
        print("--- Warnings ---")
        for w in metrics["warnings"]:
            print(f"  [WARN] {w}")
        print()

    if metrics.get("errors"):
        print("--- Errors (First 15) ---")
        for err in metrics["errors"][:15]:
            print(f"  [FAIL] {err}")
        if len(metrics["errors"]) > 15:
            print(f"  ... and {len(metrics['errors']) - 15} more errors.")
        print()


def main():
    parser = argparse.ArgumentParser(description="StandSpec AI Benchmark Validator")
    parser.add_argument("--input", "-i", type=str, help="Path to benchmark JSONL file to validate")
    parser.add_argument("--strict", action="store_true", help="Enforce strict distribution and HN coverage checks")
    parser.add_argument("--strict-isolation", action="store_true", help="Enforce zero lexical leakage in implicit queries")
    parser.add_argument("--leakage-check", action="store_true", help="Perform split leakage check between train and test")
    parser.add_argument("--temporal-split", action="store_true", help="Verify strict temporal split order between train and test")
    parser.add_argument("--train", type=str, help="Train/Dev split JSONL path (for leakage check)")
    parser.add_argument("--test", type=str, help="Test/Validation split JSONL path (for leakage check)")
    parser.add_argument("--graph", type=str, default="data/processed/standards_graph.json", help="Path to standards_graph.json for neighborhood checks")

    args = parser.parse_args()

    if args.leakage_check:
        if not args.train or not args.test:
            print("Error: --train and --test required for --leakage-check")
            sys.exit(1)
        graph_p = Path(args.graph) if args.graph and Path(args.graph).exists() else None
        clean, report = check_leakage(Path(args.train), Path(args.test), graph_path=graph_p, temporal_split=args.temporal_split)
        print("=" * 70)
        print("Zero-Leakage Verification Report (BENCHMARK_SPLIT_POLICY.md)")
        print(f"Train File: {args.train}")
        print(f"Test File:  {args.test}")
        print(f"Leakage Verdict: {'CLEAN (ZERO LEAKAGE)' if clean else 'LEAKAGE DETECTED'}")
        print("=" * 70)
        print(f"1. Exact Standard Overlaps:          {report['leakage_exact_count']}")
        print(f"2. Base Standard Family Overlaps:    {report['leakage_family_count']}")
        print(f"3. Product Family Overlaps:          {report['leakage_product_count']}")
        print(f"4. Organization Overlaps:            {report['leakage_org_count']}")
        print(f"5. Near-Duplicate Queries (> 0.75):  {report['leakage_near_duplicates_count']}")
        print(f"6. Graph Neighborhood Overlaps (>0.5):{report['leakage_graph_neighborhood_count']}")
        print(f"7. Hard Negative vs Train Gold:      {report['leakage_hard_negatives_count']}")
        if args.temporal_split:
            print(f"8. Temporal Split Violations:        {report['temporal_violations_count']}")
            if report.get('max_train_eval_date') and report.get('min_test_eval_date'):
                print(f"   max(train eval_date): {report['max_train_eval_date']}")
                print(f"   min(test  eval_date): {report['min_test_eval_date']}")

        if not clean:
            if report["leakage_exact_instances"]:
                print("\nExact Leakage Samples:")
                for qid, s in report["leakage_exact_instances"]:
                    print(f"  Test Query {qid} -> {s}")
            if report["leakage_family_instances"]:
                print("\nFamily Overlap Samples:")
                for qid, s, base in report["leakage_family_instances"]:
                    print(f"  Test Query {qid} -> {s} (base: {base})")
            if report["leakage_near_duplicates_instances"]:
                print("\nNear-Duplicate Query Samples:")
                for qid, tr_qid, jacc in report["leakage_near_duplicates_instances"]:
                    print(f"  Test Query {qid} ~ Train Query {tr_qid} (Jaccard: {jacc})")
            if report["leakage_graph_neighborhood_instances"]:
                print("\nGraph Neighborhood Overlap Samples:")
                for qid, tr_qid, jacc in report["leakage_graph_neighborhood_instances"]:
                    print(f"  Test Query {qid} ~ Train Query {tr_qid} (Graph Jaccard: {jacc})")
            if report["leakage_hard_negatives_instances"]:
                print("\nHard Negative vs Train Gold Overlap Samples:")
                for qid, s in report["leakage_hard_negatives_instances"]:
                    print(f"  Test Hard Negative {s} in Query {qid} is a Train Gold Standard!")
            for v in report["temporal_violations"]:
                print(f"  Temporal Violation: {v}")
            sys.exit(1)
        sys.exit(0)

    if not args.input:
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    schema = load_schema()
    success, metrics = validate_file(input_path, schema, strict=args.strict, strict_isolation=args.strict_isolation)
    print_report(input_path, success, metrics)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
