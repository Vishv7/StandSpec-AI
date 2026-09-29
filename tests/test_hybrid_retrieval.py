"""
Tests for Hybrid Retrieval Subsystem (Phases 9, 10, 11, 12).
Verifies dense retrieval, RRF fusion, cycle-safe graph expansion,
and cross-encoder reranking.
"""

import pytest
from src.retrieval import (
    BM25Retriever,
    DenseRetriever,
    reciprocal_rank_fusion,
    GraphCandidateExpander,
    CrossEncoderReranker,
)


@pytest.fixture
def sample_corpus():
    return [
        {
            "id": "IS 7098 (Part 2):2011",
            "designation": "IS 7098 (Part 2):2011",
            "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables For Working Voltages From 3.3 kV Up To And Including 33 kV",
            "scope": "Covers requirements for armoring, insulation thickness, and electrical testing of 11 kV to 33 kV cables.",
            "committee": "ETD 09",
            "ics_codes": ["29.060.20"],
        },
        {
            "id": "IS 1554 (Part 1):1988",
            "designation": "IS 1554 (Part 1):1988",
            "title": "PVC Insulated Electric Cables for Working Voltages up to 1100V",
            "scope": "Covers PVC insulated and PVC sheathed cables.",
            "committee": "ETD 09",
            "ics_codes": ["29.060.20"],
        },
        {
            "id": "IS 10810 (Part 53):1984",
            "designation": "IS 10810 (Part 53):1984",
            "title": "Methods of Test for Cables: Part 53 Flammability Test",
            "scope": "Specifies method of test for flammability of cables.",
            "committee": "ETD 09",
            "ics_codes": ["29.060.20"],
        },
    ]


def test_dense_retrieval_ranking(sample_corpus):
    retriever = DenseRetriever()
    retriever.index_documents(sample_corpus)

    results = retriever.retrieve("11 kV XLPE insulated cable", top_k=2)
    assert len(results) >= 1
    assert results[0]["designation"] == "IS 7098 (Part 2):2011"
    assert results[0]["score"] > 0.0


def test_reciprocal_rank_fusion():
    bm25_res = [
        {"designation": "IS 7098 (Part 2):2011", "rank": 1, "title": "XLPE Cable"},
        {"designation": "IS 1554 (Part 1):1988", "rank": 2, "title": "PVC Cable"},
    ]
    dense_res = [
        {"designation": "IS 7098 (Part 2):2011", "rank": 1, "title": "XLPE Cable"},
        {"designation": "IS 10810 (Part 53):1984", "rank": 2, "title": "Flammability Test"},
    ]

    fused = reciprocal_rank_fusion({"bm25": bm25_res, "dense": dense_res}, k=60, top_k=3)
    assert len(fused) == 3
    # IS 7098 ranked 1 in both channels -> must be rank 1 in fused
    assert fused[0]["designation"] == "IS 7098 (Part 2):2011"
    assert "bm25" in fused[0]["channel_ranks"]
    assert "dense" in fused[0]["channel_ranks"]


def test_graph_candidate_expander_cycle_safe():
    graph_dict = {
        "nodes": [
            {"id": "IS 7098 (Part 2):2011", "title": "XLPE Cable"},
            {"id": "IS 10810 (Part 53):1984", "title": "Flammability Test"},
            {"id": "IS 8130:2013", "title": "Conductors for Insulated Cables"},
        ],
        "edges": [
            {
                "source": "IS 7098 (Part 2):2011",
                "target": "IS 10810 (Part 53):1984",
                "relationship": "test_method",
                "relationship_confidence_state": "HIGH",
            },
            {
                "source": "IS 10810 (Part 53):1984",
                "target": "IS 7098 (Part 2):2011",
                "relationship": "normative_reference",
                "relationship_confidence_state": "HIGH",
            },  # Cycle
            {
                "source": "IS 7098 (Part 2):2011",
                "target": "IS 8130:2013",
                "relationship": "material_reference",
                "relationship_confidence_state": "HIGH",
            },
        ],
    }

    expander = GraphCandidateExpander(graph_dict, decay_factor=0.5)
    seed = [{"designation": "IS 7098 (Part 2):2011", "score": 1.0}]

    expanded = expander.expand(seed, top_k=5)
    desigs = [c["designation"] for c in expanded]
    assert "IS 7098 (Part 2):2011" in desigs
    assert "IS 10810 (Part 53):1984" in desigs
    assert "IS 8130:2013" in desigs
    # Check no duplicate caused by cycle
    assert len(desigs) == len(set(desigs))


def test_graph_candidate_expander_confidence_gating():
    graph_dict = {
        "nodes": [
            {"id": "IS A", "title": "Standard A"},
            {"id": "IS B", "title": "Standard B"},
            {"id": "IS C", "title": "Standard C"},
        ],
        "edges": [
            {
                "source": "IS A",
                "target": "IS B",
                "relationship": "normative_reference",
                "relationship_confidence_state": "HIGH",
            },
            {
                "source": "IS A",
                "target": "IS C",
                "relationship": "normative_reference",
                "relationship_confidence_state": "LOW",  # Must be ignored
            },
        ],
    }

    expander = GraphCandidateExpander(graph_dict)
    seed = [{"designation": "IS A", "score": 1.0}]
    expanded = expander.expand(seed)

    desigs = {c["designation"] for c in expanded}
    assert "IS B" in desigs
    assert "IS C" not in desigs  # Gated out due to LOW confidence


def test_cross_encoder_reranker_attribute_matching(sample_corpus):
    reranker = CrossEncoderReranker()
    candidates = [{"designation": d["designation"], "title": d["title"], "document": d} for d in sample_corpus]

    req_obj = {
        "requirements": {
            "product": {"value": "Crosslinked Polyethylene Cable"},
            "voltage": {"value": "11 kV"},
        }
    }

    reranked = reranker.rerank("11 kV XLPE cable", candidates, req_obj=req_obj, top_k=3)
    assert reranked[0]["designation"] == "IS 7098 (Part 2):2011"
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]
    # IS 10810 (test method) should receive a scope penalty
    assert reranked[0]["rerank_score"] > reranked[2]["rerank_score"]
