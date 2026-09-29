"""
Evaluation Package — StandSpec AI
Authoritative metrics and evaluation tooling.
"""

from src.evaluation.metrics import (
    compute_raw_retrieval_top1,
    compute_effective_candidate_top1,
    compute_verified_primary_top1,
    compute_recall_at_k,
    compute_mrr,
    compute_safety_metrics,
    compute_comprehensive_metrics,
)

__all__ = [
    "compute_raw_retrieval_top1",
    "compute_effective_candidate_top1",
    "compute_verified_primary_top1",
    "compute_recall_at_k",
    "compute_mrr",
    "compute_safety_metrics",
    "compute_comprehensive_metrics",
]
