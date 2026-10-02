"""
Reciprocal Rank Fusion (RRF) — StandSpec AI (Layer 1 Hybrid Candidate Fusion)
Fuses ranked candidate lists from disparate retrieval channels (e.g. BM25 and Dense Retrieval)
using the standard Cormack et al. reciprocal rank formula.
Deterministic, robust to disparate score distributions, and domain-parameterized.

Phase 8 Enhancement: Includes semantic similarity metadata, channel contribution
breakdown, rank-delta, and retrieval agreement classification.
"""

from collections import defaultdict
from typing import Dict, Any, List, Optional


class FusionAgreement:
    """Classification of retrieval agreement between channels."""
    STRONG = "STRONG"        # Both channels rank in top-5
    MODERATE = "MODERATE"    # Both rank in top-10
    WEAK = "WEAK"            # Both rank in top-20 but divergent
    SINGLE_CHANNEL = "SINGLE_CHANNEL"  # Only one channel retrieved


def _classify_agreement(channel_ranks: Dict[str, int]) -> str:
    """Classify agreement level from channel ranks."""
    ranks = list(channel_ranks.values())
    if len(ranks) < 2:
        return FusionAgreement.SINGLE_CHANNEL
    min_rank = min(ranks)
    max_rank = max(ranks)
    if max_rank <= 5:
        return FusionAgreement.STRONG
    elif max_rank <= 10:
        return FusionAgreement.MODERATE
    else:
        return FusionAgreement.WEAK


def _compute_rank_delta(channel_ranks: Dict[str, int]) -> Optional[int]:
    """Compute rank difference between channels. None if single channel."""
    ranks = list(channel_ranks.values())
    if len(ranks) < 2:
        return None
    return max(ranks) - min(ranks)


def _compute_channel_contributions(
    channel_ranks: Dict[str, int],
    weights: Dict[str, float],
    k: int,
) -> Dict[str, float]:
    """Compute per-channel contribution to the final RRF score."""
    contributions = {}
    total = 0.0
    for channel, rank in channel_ranks.items():
        w = weights.get(channel, 1.0)
        score = w / (k + rank)
        contributions[channel] = round(score, 6)
        total += score
    # Normalize to percentages (build separately to avoid dict mutation during iteration)
    if total > 0:
        pct_entries = {
            channel + "_pct": round(contributions[channel] / total * 100, 1)
            for channel in list(contributions.keys())
        }
        contributions.update(pct_entries)
    return contributions


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
      Each result includes Phase 8 metadata: channel_contributions,
      rank_delta, retrieval_agreement, retrieval_confidence.
    """
    if not ranked_lists:
        return []

    if weights is None:
        weights = {channel: 1.0 for channel in ranked_lists}

    rrf_scores = defaultdict(float)
    channel_ranks = defaultdict(dict)
    channel_scores = defaultdict(dict)
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
            channel_scores[desig][channel] = item.get("score", item.get("dense_score"))

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
        c_ranks = channel_ranks[desig]

        # Phase 8: Compute semantic retrieval metadata
        agreement = _classify_agreement(c_ranks)
        rank_delta = _compute_rank_delta(c_ranks)
        contributions = _compute_channel_contributions(c_ranks, weights, k)

        # Retrieval confidence: higher when both channels agree strongly
        num_channels = len(c_ranks)
        avg_rank = sum(c_ranks.values()) / num_channels if num_channels > 0 else 999
        confidence = 0.0
        if agreement == FusionAgreement.STRONG:
            confidence = 0.95
        elif agreement == FusionAgreement.MODERATE:
            confidence = 0.80
        elif agreement == FusionAgreement.WEAK:
            confidence = 0.60
        elif agreement == FusionAgreement.SINGLE_CHANNEL:
            confidence = 0.50
        # Adjust for position
        if avg_rank <= 3:
            confidence = min(confidence + 0.05, 1.0)
        elif avg_rank > 15:
            confidence = max(confidence - 0.10, 0.1)

        fused_results.append({
            "rank": rank,
            "rrf_score": round(rrf_scores[desig], 6),
            "designation": desig,
            "title": meta.get("title"),
            "channel_ranks": c_ranks,
            "channel_scores": dict(channel_scores[desig]),
            "document": meta.get("document"),
            # Phase 8 metadata
            "retrieval_metadata": {
                "channel_contributions": contributions,
                "rank_delta": rank_delta,
                "retrieval_agreement": agreement,
                "retrieval_confidence": round(confidence, 3),
                "num_channels": num_channels,
            },
        })

    return fused_results

