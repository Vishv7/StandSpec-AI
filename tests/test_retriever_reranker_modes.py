"""
Unit tests for Retriever and Reranker Mode Selection, Factory, and Fallback Transparency (Sections H, I, J).
"""

import pytest
from src.retrieval.cross_encoder import (
    create_reranker,
    RuleBasedReranker,
    NeuralCrossEncoderReranker,
    NoneReranker,
)
from src.retrieval.dense_retriever import (
    create_dense_retriever,
    DeterministicSemanticProjection,
    MultilingualDenseRetriever,
)
from src.retrieval.reranker_features import (
    DesignationAlignment,
    PartSectionAlignment,
    RoleAlignment,
    ProductCategoryAlignment,
    MaterialAlignment,
    ApplicationAlignment,
    TechnologyModifierAlignment,
    ScopeBoundary,
    Specificity,
    CandidateEvidenceAvailability,
    ProcurementIntentAlignment,
    ContradictionPenalty,
    ScoringPolicy,
    FeatureState,
)


def test_reranker_factory_modes():
    """Verify factory constructs appropriate rerankers for all modes."""
    rule_reranker = create_reranker(mode="rule_based")
    assert isinstance(rule_reranker, RuleBasedReranker)
    assert rule_reranker.reranker_type == "rule_based"
    assert rule_reranker.effective_mode == "rule_based"
    assert rule_reranker.model_loaded is True
    assert rule_reranker.fallback_used is False

    none_reranker = create_reranker(mode="none")
    assert isinstance(none_reranker, NoneReranker)
    assert none_reranker.reranker_type == "none"
    assert none_reranker.effective_mode == "none"

    neural_reranker = create_reranker(mode="neural", model_name="non-existent/dummy-model-test")
    assert isinstance(neural_reranker, NeuralCrossEncoderReranker)
    assert neural_reranker.reranker_type == "neural"
    # In hermetic offline environment, dummy model load fails gracefully
    assert neural_reranker.model_loaded is False
    assert neural_reranker.fallback_used is True
    assert neural_reranker.effective_mode == "RULE_BASED_FALLBACK"
    assert "Neural cross-encoder load failed" in neural_reranker.fallback_reason


def test_dense_retriever_factory_modes():
    """Verify dense retriever factory and transparent metadata reporting."""
    det_retriever = create_dense_retriever(mode="deterministic")
    assert isinstance(det_retriever, DeterministicSemanticProjection)
    assert det_retriever.retriever_type == "dense_deterministic"
    assert det_retriever.effective_mode in ("DENSE_DETERMINISTIC", "DETERMINISTIC_DENSE_FALLBACK")
    assert det_retriever.model_loaded is True
    assert det_retriever.fallback_used is False
    assert det_retriever.embedding_dimension == 384

    neural_retriever = create_dense_retriever(mode="neural", model_name="non-existent/dummy-neural-model")
    assert isinstance(neural_retriever, MultilingualDenseRetriever)
    assert neural_retriever.retriever_type == "dense_neural"
    # When model fails to load, transparently flags fallback mode
    assert neural_retriever.model_loaded is False
    assert neural_retriever.fallback_used is True
    assert neural_retriever.effective_mode in ("HASHED_FALLBACK", "DETERMINISTIC_DENSE_FALLBACK")
    assert "Neural embedding model load failed" in neural_retriever.fallback_reason


def test_none_reranker_passthrough():
    """Verify NoneReranker passes candidates without reordering."""
    reranker = create_reranker(mode="none")
    cands = [
        {"designation": "IS 100", "score": 0.9},
        {"designation": "IS 200", "score": 0.8},
    ]
    reranked = reranker.rerank("some query", cands)
    assert len(reranked) == 2
    assert reranked[0]["designation"] == "IS 100"
    assert reranked[1]["designation"] == "IS 200"
    assert reranked[0]["reranker_metadata"]["effective_mode"] == "none"


def test_12_features_structured_results():
    """Verify each of the 12 features returns valid FeatureResult."""
    features = [
        DesignationAlignment(),
        PartSectionAlignment(),
        RoleAlignment(),
        ProductCategoryAlignment(),
        MaterialAlignment(),
        ApplicationAlignment(),
        TechnologyModifierAlignment(),
        ScopeBoundary(),
        Specificity(),
        CandidateEvidenceAvailability(),
        ProcurementIntentAlignment(),
        ContradictionPenalty(),
    ]

    cand = {
        "designation": "IS 7098 (Part 2):2011",
        "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables",
        "document": {
            "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables",
            "scope": "Prescribes requirements for crosslinked polyethylene insulated cables for working voltages 3.3 kV up to 33 kV.",
        },
        "is_hydrated": True,
    }
    query = "Supply of 11 kV XLPE insulated power cables Part 2"

    results = []
    for f in features:
        res = f.evaluate(query, cand)
        assert res.feature_name == f.name
        assert isinstance(res.state, FeatureState)
        assert isinstance(res.score_delta, float)
        assert isinstance(res.evidence, str)
        results.append(res)

    policy = ScoringPolicy()
    score, signals, diag = policy.score(results, cand)
    assert 0.0 <= score <= 1.0
    assert "PartSectionAlignment" in diag
    assert diag["PartSectionAlignment"]["state"] == "MATCH"


def test_why_ranked_above_explainability():
    """Verify ScoringPolicy generates human-readable comparison between candidates."""
    policy = ScoringPolicy()
    cand_a = {
        "designation": "IS 7098 (Part 2):2011",
        "rerank_score": 0.92,
        "rerank_diagnostics": {
            "DesignationAlignment": {"score_delta": 4.0, "state": "MATCH", "evidence": "Matching cable specification"},
            "MaterialAlignment": {"score_delta": 2.5, "state": "MATCH", "evidence": "XLPE insulation matched"},
        }
    }
    cand_b = {
        "designation": "IS 1554 (Part 1):1988",
        "rerank_score": 0.35,
        "rerank_diagnostics": {
            "DesignationAlignment": {"score_delta": -3.0, "state": "MISMATCH", "evidence": "Different standard"},
            "MaterialAlignment": {"score_delta": -4.0, "state": "MISMATCH", "evidence": "PVC insulation instead of XLPE"},
        }
    }

    explanation = policy.why_ranked_above(cand_a, cand_b)
    assert "IS 7098 (Part 2):2011" in explanation
    assert "IS 1554 (Part 1):1988" in explanation
    assert "MaterialAlignment" in explanation
