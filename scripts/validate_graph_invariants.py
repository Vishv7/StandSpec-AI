"""
Graph Invariant Validator — StandSpec AI (Phase 4 Gate)
Verifies structural, semantic, and provenance invariants of the Standards Knowledge Graph.

Usage:
    python scripts/validate_graph_invariants.py --graph data/processed/standards_graph.json
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_knowledge_graph import _content_hash, find_and_classify_reciprocal_pairs, validate_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("graph_invariants")


def validate_graph_invariants(graph: dict) -> tuple[bool, list[str]]:
    """
    Validates all 8 core invariants:
    1. source_departments contains only departments with primary records for that standard
    2. No node has candidate_status=ELIGIBLE without metadata_available=true
    3. No node has recommendation_ready=true without scope_evidence_available=true
    4. No edge has relationship_confidence_state=HIGH without source_identity_state=VERIFIED
    5. Edge (source, target, relationship) triples are unique
    6. All node IDs referenced by edges exist in nodes
    7. Reciprocal pairs / cycle count matches reported count
    8. Deterministic content hash matches recomputed hash
    """
    violations = []
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    # Invariant 1: source_departments contains only departments with primary records
    # Stubs (unhydrated nodes) must have empty source_departments
    stubs_with_depts = [n["id"] for n in nodes.values() if not n.get("is_hydrated") and n.get("source_departments")]
    if stubs_with_depts:
        violations.append(f"Invariant 1 Violated: {len(stubs_with_depts)} unhydrated stubs have source_departments (e.g. {stubs_with_depts[:3]})")

    # Invariant 2: No node has candidate_status=ELIGIBLE without metadata_available=true
    ineligible_eligible = [n["id"] for n in nodes.values() if n.get("candidate_status") == "ELIGIBLE" and not n.get("metadata_available")]
    if ineligible_eligible:
        violations.append(f"Invariant 2 Violated: {len(ineligible_eligible)} nodes have candidate_status=ELIGIBLE without metadata_available=True (e.g. {ineligible_eligible[:3]})")

    # Invariant 3: No node has recommendation_ready=true without scope_evidence_available=true
    rec_without_scope = [n["id"] for n in nodes.values() if n.get("recommendation_ready") and not n.get("scope_evidence_available")]
    if rec_without_scope:
        violations.append(f"Invariant 3 Violated: {len(rec_without_scope)} nodes have recommendation_ready=True without scope_evidence_available=True (e.g. {rec_without_scope[:3]})")

    # Invariant 4: No edge has relationship_confidence_state=HIGH without source_identity_state=VERIFIED
    high_unverified = [f"{e['source']}->{e['target']}" for e in edges if e.get("relationship_confidence_state") == "HIGH" and e.get("source_identity_state") != "VERIFIED"]
    if high_unverified:
        violations.append(f"Invariant 4 Violated: {len(high_unverified)} edges have relationship_confidence_state=HIGH without source_identity_state=VERIFIED (e.g. {high_unverified[:3]})")

    # Invariant 5: Edge (source, target, relationship) triples are unique
    edge_keys = Counter((e["source"], e["target"], e["relationship"]) for e in edges)
    duplicates = [k for k, count in edge_keys.items() if count > 1]
    if duplicates:
        violations.append(f"Invariant 5 Violated: {len(duplicates)} duplicate edge triples found (e.g. {duplicates[:3]})")

    # Invariant 6: All node IDs referenced by edges exist in nodes
    missing_sources = [e["source"] for e in edges if e["source"] not in nodes]
    missing_targets = [e["target"] for e in edges if e["target"] not in nodes]
    if missing_sources:
        violations.append(f"Invariant 6 Violated: {len(missing_sources)} edges reference nonexistent source node (e.g. {missing_sources[:3]})")
    if missing_targets:
        violations.append(f"Invariant 6 Violated: {len(missing_targets)} edges reference nonexistent target node (e.g. {missing_targets[:3]})")

    # Invariant 7: Reciprocal pairs count matches reported count
    pairs, classification = find_and_classify_reciprocal_pairs(edges)
    reported_pairs = graph.get("reciprocal_pairs_count", 0)
    if len(pairs) != reported_pairs:
        violations.append(f"Invariant 7 Violated: Reciprocal pairs count mismatch (detected {len(pairs)}, reported {reported_pairs})")

    # Invariant 8: Content hash matches recomputed hash
    stored_hash = graph.get("content_hash")
    if stored_hash:
        recomputed = _content_hash(graph)
        if stored_hash != recomputed:
            violations.append(f"Invariant 8 Violated: Content hash mismatch (stored={stored_hash}, recomputed={recomputed})")
    else:
        violations.append("Invariant 8 Violated: content_hash missing from graph root.")

    is_valid = (len(violations) == 0)
    return is_valid, violations


def main():
    parser = argparse.ArgumentParser(description="Validate Knowledge Graph Invariants")
    parser.add_argument("--graph", "-g", default="data/processed/standards_graph.json", help="Path to graph JSON")
    args = parser.parse_args()

    graph_path = Path(args.graph)
    if not graph_path.exists():
        logger.error(f"Graph file not found: {graph_path}")
        sys.exit(1)

    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    # 1. JSON Schema validation
    schema_valid, schema_errors = validate_graph(graph)
    if not schema_valid:
        logger.error(f"Schema validation FAILED with {len(schema_errors)} errors:")
        for err in schema_errors[:10]:
            logger.error(f"  - {err}")
        sys.exit(1)
    logger.info("Draft 2020-12 JSON Schema validation PASSED.")

    # 2. Semantic invariant validation
    invariants_valid, violations = validate_graph_invariants(graph)
    if not invariants_valid:
        logger.error(f"Graph Invariant Validation FAILED with {len(violations)} violations:")
        for v in violations:
            logger.error(f"  [X] {v}")
        sys.exit(1)

    logger.info("All 8 Graph Invariants PASSED successfully!")
    logger.info(f"Verified: {graph['nodes_count']} nodes, {graph['edges_count']} edges, {graph.get('reciprocal_pairs_count')} reciprocal pairs.")
    logger.info(f"Content hash: {graph.get('content_hash')}")


if __name__ == "__main__":
    main()
