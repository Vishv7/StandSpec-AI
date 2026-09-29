"""
Graph Standard Role Enricher — StandSpec AI (Phase P1-B)
Enriches all nodes in standards_graph.json with:
  - standard_role
  - role_confidence
  - role_reason
  - role_source
  - role_classifier_version

Recomputes deterministic content_hash and validates graph invariants.
"""

import json
import logging
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.recommendation.role_classifier import RoleClassifier
from scripts.build_knowledge_graph import _content_hash, validate_graph
from scripts.validate_graph_invariants import validate_graph_invariants

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("enrich_graph_roles")


def enrich_graph_roles(graph_path: Path):
    logger.info(f"Loading graph from {graph_path}...")
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    nodes = graph.get("nodes", [])
    logger.info(f"Classifying and persisting roles for {len(nodes)} nodes...")

    role_counts = {}
    for node in nodes:
        role_info = RoleClassifier.classify_with_evidence(node)
        node["standard_role"] = role_info["standard_role"]
        node["role_confidence"] = role_info["role_confidence"]
        node["role_reason"] = role_info["role_reason"]
        node["role_source"] = role_info["role_source"]
        node["role_classifier_version"] = "1.0.0-phase-d"

        role = role_info["standard_role"]
        role_counts[role] = role_counts.get(role, 0) + 1

    logger.info(f"Role distribution: {role_counts}")

    # Recompute content hash
    graph["content_hash"] = _content_hash(graph)
    logger.info(f"Recomputed content_hash: {graph['content_hash']}")

    # Validate against schema
    is_valid_schema, schema_errors = validate_graph(graph)
    if not is_valid_schema:
        logger.error(f"Graph schema validation failed with {len(schema_errors)} errors:")
        for err in schema_errors[:10]:
            logger.error(f"  {err}")
        sys.exit(1)
    logger.info("Graph schema validation PASSED.")

    # Validate invariants
    is_valid_inv, inv_errors = validate_graph_invariants(graph)
    if not is_valid_inv:
        logger.error(f"Graph invariant validation failed with {len(inv_errors)} errors:")
        for err in inv_errors[:10]:
            logger.error(f"  {err}")
        sys.exit(1)
    logger.info("Graph invariant validation PASSED.")

    # Save enriched graph
    logger.info(f"Saving enriched graph to {graph_path}...")
    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    logger.info("Graph enrichment successfully completed.")
    return graph["content_hash"]


if __name__ == "__main__":
    target = PROJECT_ROOT / "data" / "processed" / "standards_graph.json"
    enrich_graph_roles(target)
