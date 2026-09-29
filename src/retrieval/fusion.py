"""
Reciprocal Rank Fusion (RRF) — StandSpec AI (Layer 1 Hybrid Candidate Fusion)
Fuses ranked candidate lists from disparate retrieval channels (e.g. BM25 and Dense Retrieval)
using the standard Cormack et al. reciprocal rank formula.
Deterministic, robust to disparate score distributions, and domain-parameterized.
"""

from collections import defaultdict


def reciprocal_rank_fusion(
    ranked_lists: dict[str, list[dict]],
    k: int = 60,
    weights: dict[str, float] = None,
    top_k: int = 20,
) -> list[dict]:
    """
    Perform Reciprocal Rank Fusion over multiple ranked result sets.

    Parameters:
    - ranked_lists: dict mapping channel name (e.g. 'bm25', 'dense') to a list of result dicts.
      Each result dict must contain 'designation' (or 'id').
    - k: RRF smoothing constant (standard default is 60).
    - weights: optional channel weights dict (e.g. {'bm25': 1.0, 'dense': 1.0}).
    - top_k: maximum number of fused results to return.

    Returns:
    - List of fused result dicts sorted by descending RRF score.
    """
    if not ranked_lists:
        return []

    if weights is None:
        weights = {channel: 1.0 for channel in ranked_lists}

    rrf_scores = defaultdict(float)
    channel_ranks = defaultdict(dict)
    candidate_metadata = {}

    for channel, results in ranked_lists.items():
        w = weights.get(channel, 1.0)
        for rank, item in enumerate(results, 1):
            desig = item.get("designation") or item.get("id")
            if not desig:
                continue

            # RRF formula: w / (k + r)
            rrf_scores[desig] += w / (k + rank)
            channel_ranks[desig][channel] = rank

            if desig not in candidate_metadata:
                candidate_metadata[desig] = {
                    "designation": desig,
                    "title": item.get("title"),
                    "document": item.get("document", item),
                }

    # Sort descending by RRF score; break ties deterministically by designation string
    sorted_candidates = sorted(
        rrf_scores.keys(),
        key=lambda d: (-rrf_scores[d], d)
    )

    fused_results = []
    for rank, desig in enumerate(sorted_candidates[:top_k], 1):
        meta = candidate_metadata[desig]
        fused_results.append({
            "rank": rank,
            "rrf_score": round(rrf_scores[desig], 6),
            "designation": desig,
            "title": meta.get("title"),
            "channel_ranks": channel_ranks[desig],
            "document": meta.get("document"),
        })

    return fused_results
