"""
Retrieval Diagnostics & Instrumentation — StandSpec AI (Phase 7, Checkpoint 3)
PS 26108 §10: Structured retrieval pipeline instrumentation.

Provides structured diagnostic data for every retrieval event:
  - Per-channel retrieval statistics (BM25, Dense, RRF)
  - Recall estimation at various K thresholds
  - Channel agreement/disagreement analysis
  - Retrieval failure root-cause classification
  - Query-to-retrieval quality signals

This module is observational only — it does NOT modify retrieval behavior.
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from enum import Enum
import time


class RetrievalFailureMode(str, Enum):
    """Root-cause classification for retrieval failures."""
    ABSENT_FROM_KB = "ABSENT_FROM_KB"                    # Gold standard not in knowledge graph
    UNHYDRATED_STUB = "UNHYDRATED_STUB"                  # Node exists but scope/metadata missing
    LEXICAL_GAP = "LEXICAL_GAP"                          # BM25 missed due to vocabulary mismatch
    SEMANTIC_GAP = "SEMANTIC_GAP"                        # Dense missed due to embedding space gap
    BOTH_CHANNELS_MISS = "BOTH_CHANNELS_MISS"            # Neither BM25 nor Dense retrieved the target
    LOW_FUSION_RANK = "LOW_FUSION_RANK"                  # Retrieved but ranked too low in fusion
    GRAPH_EXPANSION_MISS = "GRAPH_EXPANSION_MISS"        # Family/part expansion didn't surface target
    CROSS_ENCODER_DISPLACEMENT = "CROSS_ENCODER_DISPLACEMENT"  # Reranker demoted the target


class ChannelAgreement(str, Enum):
    """Agreement classification between BM25 and Dense retrieval channels."""
    STRONG_AGREEMENT = "STRONG_AGREEMENT"      # Both channels rank target in top-5
    MODERATE_AGREEMENT = "MODERATE_AGREEMENT"  # Both rank in top-10 but not top-5
    WEAK_AGREEMENT = "WEAK_AGREEMENT"          # Both rank in top-20 but divergent ranks
    BM25_ONLY = "BM25_ONLY"                    # Only BM25 retrieved the target
    DENSE_ONLY = "DENSE_ONLY"                  # Only Dense retrieved the target
    NEITHER = "NEITHER"                        # Neither channel retrieved the target


class RetrievalDiagnostics:
    """
    Captures and analyzes retrieval pipeline diagnostics for a single query.
    """

    def __init__(self):
        self.query_text: str = ""
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.bm25_results: List[Dict] = []
        self.dense_results: List[Dict] = []
        self.fused_results: List[Dict] = []
        self.expanded_results: List[Dict] = []
        self.reranked_results: List[Dict] = []
        self.channel_diagnostics: Dict[str, Dict[str, Any]] = {}

    def start(self, query_text: str):
        self.query_text = query_text
        self.start_time = time.time()

    def finish(self):
        self.end_time = time.time()

    @property
    def elapsed_ms(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return round((self.end_time - self.start_time) * 1000, 2)
        return None

    def record_bm25(self, results: List[Dict]):
        self.bm25_results = results or []

    def record_dense(self, results: List[Dict]):
        self.dense_results = results or []

    def record_fusion(self, results: List[Dict]):
        self.fused_results = results or []

    def record_expansion(self, results: List[Dict]):
        self.expanded_results = results or []

    def record_reranked(self, results: List[Dict]):
        self.reranked_results = results or []

    def _get_designations(self, results: List[Dict]) -> List[str]:
        """Extract designations from a list of result dicts."""
        desigs = []
        for r in results:
            d = r.get("designation") or (r.get("document") or {}).get("designation")
            if d:
                desigs.append(d)
        return desigs

    def compute_channel_agreement(self, target_designation: str) -> ChannelAgreement:
        """Classify agreement between BM25 and Dense for a target."""
        bm25_desigs = self._get_designations(self.bm25_results)
        dense_desigs = self._get_designations(self.dense_results)

        in_bm25 = target_designation in bm25_desigs
        in_dense = target_designation in dense_desigs

        if not in_bm25 and not in_dense:
            return ChannelAgreement.NEITHER

        if in_bm25 and not in_dense:
            return ChannelAgreement.BM25_ONLY

        if in_dense and not in_bm25:
            return ChannelAgreement.DENSE_ONLY

        # Both retrieved it — check rank agreement
        bm25_rank = bm25_desigs.index(target_designation) + 1
        dense_rank = dense_desigs.index(target_designation) + 1

        if bm25_rank <= 5 and dense_rank <= 5:
            return ChannelAgreement.STRONG_AGREEMENT
        elif bm25_rank <= 10 and dense_rank <= 10:
            return ChannelAgreement.MODERATE_AGREEMENT
        else:
            return ChannelAgreement.WEAK_AGREEMENT

    def diagnose_retrieval_failure(
        self,
        target_designation: str,
        graph_nodes: Optional[Set[str]] = None,
    ) -> List[RetrievalFailureMode]:
        """
        Classify why a target standard was not retrieved or ranked poorly.
        Returns list of applicable failure modes (may be multiple).
        """
        failure_modes: List[RetrievalFailureMode] = []

        # Check if target exists in knowledge base
        if graph_nodes is not None and target_designation not in graph_nodes:
            failure_modes.append(RetrievalFailureMode.ABSENT_FROM_KB)
            return failure_modes

        bm25_desigs = self._get_designations(self.bm25_results)
        dense_desigs = self._get_designations(self.dense_results)
        fused_desigs = self._get_designations(self.fused_results)
        expanded_desigs = self._get_designations(self.expanded_results)
        reranked_desigs = self._get_designations(self.reranked_results)

        in_bm25 = target_designation in bm25_desigs
        in_dense = target_designation in dense_desigs

        if not in_bm25 and not in_dense:
            failure_modes.append(RetrievalFailureMode.BOTH_CHANNELS_MISS)
            # Determine if lexical or semantic gap
            failure_modes.append(RetrievalFailureMode.LEXICAL_GAP)
            failure_modes.append(RetrievalFailureMode.SEMANTIC_GAP)
            return failure_modes

        if not in_bm25:
            failure_modes.append(RetrievalFailureMode.LEXICAL_GAP)
        if not in_dense:
            failure_modes.append(RetrievalFailureMode.SEMANTIC_GAP)

        # Check if fused but ranked too low
        if target_designation in fused_desigs:
            fused_rank = fused_desigs.index(target_designation) + 1
            if fused_rank > 10:
                failure_modes.append(RetrievalFailureMode.LOW_FUSION_RANK)

        # Check if graph expansion missed
        if target_designation not in expanded_desigs and target_designation in fused_desigs:
            failure_modes.append(RetrievalFailureMode.GRAPH_EXPANSION_MISS)

        # Check if reranker displaced
        if target_designation in expanded_desigs and target_designation not in reranked_desigs[:10]:
            if reranked_desigs and target_designation in reranked_desigs:
                reranked_rank = reranked_desigs.index(target_designation) + 1
                if reranked_rank > 5:
                    failure_modes.append(RetrievalFailureMode.CROSS_ENCODER_DISPLACEMENT)

        return failure_modes

    def compute_recall_at_k(
        self,
        gold_designations: Set[str],
        k_values: List[int] = None,
    ) -> Dict[str, Dict[int, float]]:
        """
        Compute recall@k for each retrieval stage.
        """
        if not gold_designations:
            return {}

        if k_values is None:
            k_values = [1, 3, 5, 10, 20]

        stages = {
            "bm25": self._get_designations(self.bm25_results),
            "dense": self._get_designations(self.dense_results),
            "fused": self._get_designations(self.fused_results),
            "expanded": self._get_designations(self.expanded_results),
            "reranked": self._get_designations(self.reranked_results),
        }

        recall = {}
        for stage_name, desigs in stages.items():
            recall[stage_name] = {}
            for k in k_values:
                top_k = set(desigs[:k])
                hits = len(gold_designations & top_k)
                recall[stage_name][k] = round(hits / len(gold_designations), 4) if gold_designations else 0.0

        return recall

    def get_summary(self) -> Dict[str, Any]:
        """Generate a summary of retrieval diagnostics."""
        return {
            "query_text": self.query_text[:200] if self.query_text else "",
            "elapsed_ms": self.elapsed_ms,
            "channel_counts": {
                "bm25": len(self.bm25_results),
                "dense": len(self.dense_results),
                "fused": len(self.fused_results),
                "expanded": len(self.expanded_results),
                "reranked": len(self.reranked_results),
            },
            "top_5_fused": self._get_designations(self.fused_results)[:5],
            "top_5_reranked": self._get_designations(self.reranked_results)[:5],
        }


def enrich_error_taxonomy_with_retrieval(
    error_labels: List[str],
    diagnostics: RetrievalDiagnostics,
    gold_designations: Set[str],
) -> List[str]:
    """
    Enrich error taxonomy labels with granular retrieval failure modes.

    Takes existing error labels and adds specific retrieval failure
    classifications based on diagnostic data.
    """
    enriched = list(error_labels)

    for gold in gold_designations:
        failure_modes = diagnostics.diagnose_retrieval_failure(gold)
        for mode in failure_modes:
            label = f"RETRIEVAL_{mode.value}"
            if label not in enriched:
                enriched.append(label)

        agreement = diagnostics.compute_channel_agreement(gold)
        agreement_label = f"CHANNEL_{agreement.value}"
        if agreement_label not in enriched:
            enriched.append(agreement_label)

    return enriched
