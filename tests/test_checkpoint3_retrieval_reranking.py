"""
Regression Tests for Checkpoint 3: Retrieval / Reranking Improvements
PS 26108 Phases 7-8.

Phase 7: Retrieval Instrumentation & Error Taxonomy
Phase 8: Dense / Semantic Retrieval Metadata
"""

import pytest
from src.retrieval.retrieval_diagnostics import (
    RetrievalDiagnostics,
    RetrievalFailureMode,
    ChannelAgreement,
    enrich_error_taxonomy_with_retrieval,
)
from src.retrieval.fusion import (
    reciprocal_rank_fusion,
    FusionAgreement,
    _classify_agreement,
    _compute_rank_delta,
)
from src.evaluation.error_taxonomy import ErrorLabel


# ============================================================================
# Phase 7: Retrieval Diagnostics
# ============================================================================

class TestRetrievalDiagnostics:
    """Tests for retrieval pipeline instrumentation."""

    @pytest.fixture
    def diagnostics(self):
        d = RetrievalDiagnostics()
        d.start("Supply of HDPE pipes for potable water")
        d.record_bm25([
            {"designation": "IS 4984:1995", "rank": 1, "score": 25.3},
            {"designation": "IS 4984:2016", "rank": 2, "score": 23.1},
            {"designation": "IS 7634:1975", "rank": 3, "score": 18.0},
            {"designation": "IS 14333:1996", "rank": 4, "score": 15.2},
        ])
        d.record_dense([
            {"designation": "IS 4984:2016", "rank": 1, "score": 0.89},
            {"designation": "IS 4984:1995", "rank": 2, "score": 0.85},
            {"designation": "IS 14333:1996", "rank": 3, "score": 0.72},
            {"designation": "IS 7328:1992", "rank": 4, "score": 0.68},
        ])
        d.record_fusion([
            {"designation": "IS 4984:2016", "rank": 1},
            {"designation": "IS 4984:1995", "rank": 2},
            {"designation": "IS 14333:1996", "rank": 3},
            {"designation": "IS 7634:1975", "rank": 4},
            {"designation": "IS 7328:1992", "rank": 5},
        ])
        d.finish()
        return d

    def test_channel_agreement_strong(self, diagnostics):
        """Both channels rank IS 4984:2016 in top-5 → STRONG."""
        agreement = diagnostics.compute_channel_agreement("IS 4984:2016")
        assert agreement == ChannelAgreement.STRONG_AGREEMENT

    def test_channel_agreement_bm25_only(self, diagnostics):
        """IS 7634:1975 only in BM25 → BM25_ONLY."""
        agreement = diagnostics.compute_channel_agreement("IS 7634:1975")
        assert agreement == ChannelAgreement.BM25_ONLY

    def test_channel_agreement_dense_only(self, diagnostics):
        """IS 7328:1992 only in Dense → DENSE_ONLY."""
        agreement = diagnostics.compute_channel_agreement("IS 7328:1992")
        assert agreement == ChannelAgreement.DENSE_ONLY

    def test_channel_agreement_neither(self, diagnostics):
        """IS 9999:2099 not in any channel → NEITHER."""
        agreement = diagnostics.compute_channel_agreement("IS 9999:2099")
        assert agreement == ChannelAgreement.NEITHER

    def test_recall_at_k(self, diagnostics):
        """Recall@K must be computed per stage."""
        gold = {"IS 4984:2016", "IS 14333:1996"}
        recall = diagnostics.compute_recall_at_k(gold, k_values=[1, 3, 5])

        # BM25: IS 4984:2016 at rank 2, IS 14333 at rank 4
        assert recall["bm25"][1] == 0.0  # Neither in top-1 for bm25 (rank 1 = IS 4984:1995)
        assert recall["bm25"][3] == 0.5  # IS 4984:2016 at rank 2 only
        assert recall["bm25"][5] == 1.0  # Both in top-5

        # Dense: IS 4984:2016 at rank 1, IS 14333 at rank 3
        assert recall["dense"][1] == 0.5
        assert recall["dense"][3] == 1.0

    def test_failure_diagnosis_absent(self, diagnostics):
        """Standard not in KB → ABSENT_FROM_KB."""
        graph_nodes = {"IS 4984:1995", "IS 4984:2016"}
        modes = diagnostics.diagnose_retrieval_failure("IS 99999:2099", graph_nodes=graph_nodes)
        assert RetrievalFailureMode.ABSENT_FROM_KB in modes

    def test_failure_diagnosis_both_miss(self, diagnostics):
        """Standard not in any channel → BOTH_CHANNELS_MISS."""
        modes = diagnostics.diagnose_retrieval_failure("IS 88888:2020")
        assert RetrievalFailureMode.BOTH_CHANNELS_MISS in modes

    def test_failure_diagnosis_lexical_gap(self, diagnostics):
        """Standard in dense but not BM25 → LEXICAL_GAP."""
        modes = diagnostics.diagnose_retrieval_failure("IS 7328:1992")
        assert RetrievalFailureMode.LEXICAL_GAP in modes

    def test_summary(self, diagnostics):
        """Summary should have all fields."""
        s = diagnostics.get_summary()
        assert "elapsed_ms" in s
        assert s["elapsed_ms"] is not None
        assert s["channel_counts"]["bm25"] == 4
        assert s["channel_counts"]["dense"] == 4
        assert s["channel_counts"]["fused"] == 5


class TestErrorTaxonomyEnrichment:
    """Tests for enriching error labels with retrieval diagnostics."""

    def test_enrichment_adds_failure_modes(self):
        d = RetrievalDiagnostics()
        d.record_bm25([{"designation": "IS 1234", "rank": 1}])
        d.record_dense([])  # Dense missed IS 5678
        d.record_fusion([{"designation": "IS 1234", "rank": 1}])

        labels = ["RETRIEVAL_MISS"]
        enriched = enrich_error_taxonomy_with_retrieval(
            labels, d, gold_designations={"IS 5678"}
        )
        assert "RETRIEVAL_MISS" in enriched
        assert any("BOTH_CHANNELS_MISS" in l for l in enriched)


class TestErrorTaxonomyLabels:
    """Tests that new error labels exist in the taxonomy."""

    def test_phase7_labels_exist(self):
        assert ErrorLabel.RETRIEVAL_MISS_SEMANTIC_GAP == "RETRIEVAL_MISS_SEMANTIC_GAP"
        assert ErrorLabel.RETRIEVAL_MISS_BOTH_CHANNELS == "RETRIEVAL_MISS_BOTH_CHANNELS"
        assert ErrorLabel.RETRIEVAL_LOW_FUSION_RANK == "RETRIEVAL_LOW_FUSION_RANK"
        assert ErrorLabel.RETRIEVAL_CROSS_ENCODER_DISPLACEMENT == "RETRIEVAL_CROSS_ENCODER_DISPLACEMENT"
        assert ErrorLabel.RETRIEVAL_GRAPH_EXPANSION_MISS == "RETRIEVAL_GRAPH_EXPANSION_MISS"
        assert ErrorLabel.MATERIAL_FAMILY_MISMATCH == "MATERIAL_FAMILY_MISMATCH"
        assert ErrorLabel.PRODUCT_FAMILY_MISMATCH == "PRODUCT_FAMILY_MISMATCH"


# ============================================================================
# Phase 8: RRF Fusion Metadata
# ============================================================================

class TestFusionAgreement:
    """Tests for fusion agreement classification."""

    def test_strong_agreement(self):
        assert _classify_agreement({"bm25": 1, "dense": 3}) == FusionAgreement.STRONG

    def test_moderate_agreement(self):
        assert _classify_agreement({"bm25": 2, "dense": 8}) == FusionAgreement.MODERATE

    def test_weak_agreement(self):
        assert _classify_agreement({"bm25": 3, "dense": 18}) == FusionAgreement.WEAK

    def test_single_channel(self):
        assert _classify_agreement({"bm25": 5}) == FusionAgreement.SINGLE_CHANNEL


class TestRankDelta:
    """Tests for rank delta computation."""

    def test_delta_computation(self):
        assert _compute_rank_delta({"bm25": 1, "dense": 5}) == 4

    def test_delta_none_single(self):
        assert _compute_rank_delta({"bm25": 3}) is None


class TestFusionMetadata:
    """Tests that RRF fusion output includes Phase 8 metadata."""

    def test_fusion_output_has_metadata(self):
        bm25 = [
            {"designation": "IS 4984", "title": "HDPE Pipes", "score": 25.0},
            {"designation": "IS 7634", "title": "Related Pipe", "score": 20.0},
        ]
        dense = [
            {"designation": "IS 4984", "title": "HDPE Pipes", "score": 0.92},
            {"designation": "IS 14333", "title": "Fittings", "score": 0.78},
        ]
        fused = reciprocal_rank_fusion(
            {"bm25": bm25, "dense": dense},
            k=60, weights={"bm25": 1.2, "dense": 0.8}, top_k=10,
        )

        assert len(fused) >= 1
        top = fused[0]

        # Must have Phase 8 retrieval_metadata
        assert "retrieval_metadata" in top
        meta = top["retrieval_metadata"]
        assert "channel_contributions" in meta
        assert "rank_delta" in meta
        assert "retrieval_agreement" in meta
        assert "retrieval_confidence" in meta
        assert "num_channels" in meta

    def test_fusion_strong_agreement_confidence(self):
        """IS 4984 ranked #1 by both channels → high confidence."""
        bm25 = [{"designation": "IS 4984", "title": "HDPE", "score": 25.0}]
        dense = [{"designation": "IS 4984", "title": "HDPE", "score": 0.95}]

        fused = reciprocal_rank_fusion(
            {"bm25": bm25, "dense": dense}, k=60,
        )
        top = fused[0]
        assert top["retrieval_metadata"]["retrieval_agreement"] == FusionAgreement.STRONG
        assert top["retrieval_metadata"]["retrieval_confidence"] >= 0.90

    def test_fusion_single_channel_lower_confidence(self):
        """Standard only in BM25 → lower confidence."""
        bm25 = [
            {"designation": "IS 4984", "title": "HDPE", "score": 25.0},
            {"designation": "IS 7634", "title": "Related", "score": 18.0},
        ]
        dense = [{"designation": "IS 4984", "title": "HDPE", "score": 0.95}]

        fused = reciprocal_rank_fusion(
            {"bm25": bm25, "dense": dense}, k=60,
        )
        # IS 7634 is only in BM25
        is_7634 = next(f for f in fused if f["designation"] == "IS 7634")
        assert is_7634["retrieval_metadata"]["retrieval_agreement"] == FusionAgreement.SINGLE_CHANNEL
        assert is_7634["retrieval_metadata"]["retrieval_confidence"] <= 0.60

    def test_fusion_has_channel_scores(self):
        """Fusion output must include per-channel scores."""
        bm25 = [{"designation": "IS 4984", "title": "HDPE", "score": 25.0}]
        dense = [{"designation": "IS 4984", "title": "HDPE", "score": 0.95}]

        fused = reciprocal_rank_fusion({"bm25": bm25, "dense": dense}, k=60)
        top = fused[0]
        assert "channel_scores" in top
        assert top["channel_scores"].get("bm25") == 25.0
        assert top["channel_scores"].get("dense") == 0.95

    def test_fusion_rank_delta(self):
        """Rank delta must reflect position difference between channels."""
        bm25 = [
            {"designation": "IS 4984", "title": "HDPE", "score": 25.0},
            {"designation": "IS 7634", "title": "Related", "score": 20.0},
        ]
        dense = [
            {"designation": "IS 7634", "title": "Related", "score": 0.85},
            {"designation": "IS 4984", "title": "HDPE", "score": 0.78},
        ]

        fused = reciprocal_rank_fusion({"bm25": bm25, "dense": dense}, k=60)
        for r in fused:
            if r["designation"] == "IS 4984":
                # BM25: rank 1, Dense: rank 2 → delta = 1
                assert r["retrieval_metadata"]["rank_delta"] == 1
            if r["designation"] == "IS 7634":
                # BM25: rank 2, Dense: rank 1 → delta = 1
                assert r["retrieval_metadata"]["rank_delta"] == 1
