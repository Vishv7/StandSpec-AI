"""
Tests for BM25 Lexical Retrieval Baseline.
Verifies domain-aware tokenization, weighting, indexing, and retrieval ranking behavior.
"""

import pytest
from src.retrieval.bm25_retriever import BM25Retriever, tokenize


def test_tokenize():
    """Verify stopword filtering and tokenization."""
    text = "Specification for Crosslinked Polyethylene (XLPE) Insulated Cables."
    tokens = tokenize(text)
    assert "crosslinked" in tokens
    assert "polyethylene" in tokens
    assert "xlpe" in tokens
    assert "cables" in tokens
    assert "for" not in tokens  # Stopword removed


def test_tokenize_standard_designations():
    """Verify standard designations are parsed into compound and base tokens."""
    text = "Refer to IS 7098 (Part 2):2011 and IS/IEC 60947-2:2016 and IEC 61439-1."
    tokens = tokenize(text)
    assert "is_7098" in tokens
    assert "7098" in tokens
    assert "is_7098_part_2" in tokens
    assert "is_iec_60947_2" in tokens
    assert "iec_61439_1" in tokens


def test_tokenize_units_and_grades():
    """Verify engineering units, ratings, and grades are properly extracted."""
    text = "Supply 11 kV 300 sq.mm XLPE cables, Fe 500D rebar, and 43 Grade cement."
    tokens = tokenize(text)
    assert "11kv" in tokens
    assert "300sqmm" in tokens
    assert "fe_500d" in tokens
    assert "fe500d" in tokens
    assert "43_grade" in tokens


def test_tokenize_multilingual():
    """Verify Unicode tokens in Indian languages (Hindi, Gujarati) are preserved."""
    hindi_text = "कंक्रीट बीम और कॉलम का निर्माण"
    hindi_tokens = tokenize(hindi_text)
    assert "कंक्रीट" in hindi_tokens
    assert "बीम" in hindi_tokens
    assert "कॉलम" in hindi_tokens

    gujarati_text = "ઔદ્યોગિક પંપિંગ મોટર્સ"
    guj_tokens = tokenize(gujarati_text)
    assert "ઔદ્યોગિક" in guj_tokens
    assert "પંપિંગ" in guj_tokens
    assert "મોટર્સ" in guj_tokens


def test_tokenize_never_drops_is_in_designations():
    """Verify standard prefix 'IS' is preserved in standard tokens."""
    tokens = tokenize("IS 1786 specification")
    assert "is_1786" in tokens
    assert "1786" in tokens


def test_bm25_retrieval_ranking():
    """Verify BM25 ranks the exact match highest."""
    corpus = [
        {
            "designation": "IS 7098 (Part 2):2011",
            "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables",
            "scope": "Covers XLPE insulated cables for working voltages from 3.3 kV up to 33 kV.",
            "committee": "ETD 09",
            "ics_codes": ["29.060.20"]
        },
        {
            "designation": "IS 1554 (Part 1):1988",
            "title": "PVC Insulated Electric Cables for Working Voltages up to 1100V",
            "scope": "Covers PVC insulated and PVC sheathed cables.",
            "committee": "ETD 09",
            "ics_codes": ["29.060.20"]
        },
        {
            "designation": "IS 16424:2016",
            "title": "Ashwagandha (Withania somnifera) Roots",
            "scope": "Prescribes requirements and methods of test for dried roots of Withania somnifera.",
            "committee": "AYD 04",
            "ics_codes": ["11.120"]
        }
    ]

    retriever = BM25Retriever()
    retriever.index_documents(corpus)

    # Query 1: Cable query should rank IS 7098 #1
    query_cable = "11 kV XLPE insulated power cables"
    results = retriever.retrieve(query_cable, top_k=3)
    assert len(results) >= 1
    assert results[0]["designation"] == "IS 7098 (Part 2):2011"
    assert "xlpe" in results[0]["matched_terms"]

    # Query 2: Herbal query should rank IS 16424 #1
    query_ayush = "Ashwagandha root powder churna"
    results_ayush = retriever.retrieve(query_ayush, top_k=3)
    assert len(results_ayush) >= 1
    assert results_ayush[0]["designation"] == "IS 16424:2016"
    assert "ashwagandha" in results_ayush[0]["matched_terms"]


def test_bm25_empty_query_returns_empty():
    """Verify empty or stopword-only queries return empty list."""
    retriever = BM25Retriever()
    retriever.index_documents([{"designation": "IS 100", "title": "Test"}])
    assert retriever.retrieve("", top_k=5) == []
    assert retriever.retrieve("and or the for", top_k=5) == []
