"""
Graph-Assisted Candidate Expansion Engine — StandSpec AI (Layer 2 Graph Expansion)
Performs cycle-safe traversal over the standards knowledge graph to discover
allied, normative, and conjunctive standards.
Enforces edge confidence constraints (HIGH / MEDIUM confidence only) and
prevents cyclic runaway using visited sets and hop attenuation.
"""

from collections import defaultdict


EXPANSION_RELATIONSHIPS = frozenset([
    "normative_reference",
    "used_in_conjunction_with",
    "test_method",
    "material_reference",
    "supersedes",
    "superseded_by",
    "installation_reference",
    "safety_reference",
    "dual_numbering",
    "equivalent_to",
    "family_series",
])

VALID_EXPANSION_CONFIDENCE = frozenset(["HIGH", "MEDIUM"])


class GraphCandidateExpander:
    """
    Cycle-Safe Knowledge Graph Expander.
    Expands an initial set of retrieved candidates along trusted relationships.
    """

    def __init__(self, graph_dict: dict = None, decay_factor: float = 0.5, max_hops: int = 1):
        self.decay_factor = decay_factor
        self.max_hops = max_hops
        self.nodes = {}
        self.adjacency = defaultdict(list)  # source -> list of (target, edge_data)

        if graph_dict:
            self.load_graph(graph_dict)

    def load_graph(self, graph_dict: dict):
        """Build node registry and forward adjacency from a standards graph dict."""
        self.nodes = {(n.get("id") or n.get("designation")): n for n in graph_dict.get("nodes", []) if n.get("id") or n.get("designation")}
        self.adjacency.clear()

        for edge in graph_dict.get("edges", []):
            src = edge.get("source")
            tgt = edge.get("target")
            if not src or not tgt:
                continue

            rel = edge.get("relationship", "normative_reference")
            conf = edge.get("relationship_confidence_state", "HIGH")
            obs = edge.get("relationship_observation", "EXPLICIT_FROM_SOURCE")

            self.adjacency[src].append({
                "target": tgt,
                "relationship": rel,
                "confidence": conf,
                "observation": obs,
                "raw_edge": edge,
            })

        # Build family series connections for multi-part standards
        family_map = defaultdict(list)
        for n in graph_dict.get("nodes", []):
            fam = n.get("family")
            base = n.get("base_number")
            node_id = n.get("id") or n.get("designation")
            if fam and base and node_id:
                family_map[(fam, base)].append(node_id)

        for (fam, base), members in family_map.items():
            if len(members) > 1:
                for m in members:
                    for other in members:
                        if m != other:
                            self.adjacency[m].append({
                                "target": other,
                                "relationship": "family_series",
                                "confidence": "HIGH",
                                "observation": "FAMILY_PART_SERIES",
                                "raw_edge": {},
                            })

    def expand(self, seed_candidates: list[dict], top_k: int = 25) -> list[dict]:
        """
        Expand initial seed candidates across valid 1-hop / 2-hop edges.

        Parameters:
        - seed_candidates: list of candidate dicts (e.g. from RRF) with 'designation' and score.
        - top_k: maximum total candidates (seeds + expanded) to return.

        Returns:
        - List of candidates including expanded items annotated with expansion provenance.
        """
        expanded_candidates = list(seed_candidates)
        visited = {c.get("designation") for c in seed_candidates if c.get("designation")}

        for seed in seed_candidates:
            seed_id = seed.get("designation")
            if not seed_id or seed_id not in self.adjacency:
                continue

            seed_score = seed.get("score") or seed.get("rrf_score", 0.01)

            # Traverse 1-hop outgoing edges
            for edge in self.adjacency[seed_id]:
                target_id = edge["target"]
                rel = edge["relationship"]
                conf = edge["confidence"]

                # 1. Filter: relationship must be an expansion relationship
                if rel not in EXPANSION_RELATIONSHIPS:
                    continue

                # 2. Filter: only HIGH and MEDIUM confidence edges
                if conf not in VALID_EXPANSION_CONFIDENCE:
                    continue

                # 3. Cycle prevention
                if target_id in visited:
                    continue

                visited.add(target_id)
                target_node = self.nodes.get(target_id, {})
                expanded_score = round(seed_score * self.decay_factor, 6)

                expanded_candidates.append({
                    "designation": target_id,
                    "title": target_node.get("title", ""),
                    "score": expanded_score,
                    "is_expanded": True,
                    "expanded_from": seed_id,
                    "expansion_relationship": rel,
                    "expansion_confidence": conf,
                    "document": target_node,
                })

        # Sort descending by score; seeds naturally maintain higher scores due to decay
        expanded_candidates.sort(
            key=lambda c: (-c.get("score", c.get("rrf_score", 0.0)), c.get("designation", ""))
        )
        return expanded_candidates[:top_k]
