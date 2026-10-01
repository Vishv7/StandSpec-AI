"""
Multilingual Procurement Query Hardening & Validation — StandSpec AI (Part 24)
Validates system behavior on Hindi, Gujarati, Hinglish, and code-mixed procurement specifications:
1. Language detection accuracy (en, hi, gu, hinglish)
2. Safe recommendation execution without unicode encoding crashes
3. End-to-end candidate retrieval on multilingual and code-mixed queries
4. Truthful language reporting in response dictionary
"""

import pytest
from src.extraction.normalizer import detect_language
from src.recommendation.engine import StandSpecRecommendationEngine


@pytest.fixture(scope="module")
def engine():
    return StandSpecRecommendationEngine.from_release()


def test_multilingual_detection_matrix():
    """Validates language detector against multiple scripts and code-mixed formats."""
    # English
    en = detect_language("Supply of 11 kV XLPE insulated power cables")
    assert en["detected"] == "en"

    # Hindi (Devanagari)
    hi = detect_language("11 केवी वितरण ट्रांसफार्मर की खरीद एवं स्थापना")
    assert hi["detected"] == "hi"
    assert hi["contains_hindi"] is True

    # Gujarati
    gu = detect_language("11 કેવી ટ્રાન્સફોર્મર સપ્લાય ટેન્ડર સરકારી કામ માટે")
    assert gu["detected"] == "gu"
    assert gu["contains_gujarati"] is True

    # Hinglish
    hinglish1 = detect_language("Substation ke liye 11 kV underground XLPE taar chahiye")
    assert hinglish1["detected"] == "hinglish"
    assert hinglish1["contains_hinglish"] is True

    hinglish2 = detect_language("Paani ki supply ke liye cast iron pipe lagana hai")
    assert hinglish2["detected"] == "hinglish"


def test_hindi_transformer_query_safety(engine):
    """Verifies a Devanagari Hindi procurement query executes cleanly and detects language."""
    hindi_query = "11 केवी वितरण ट्रांसफार्मर की आपूर्ति"
    res = engine.recommend(hindi_query)

    assert res is not None
    assert res["query"]["language"] == "hi"
    assert res["decision_state"] in (
        "PRIMARY_RECOMMENDATION_AVAILABLE",
        "CONDITIONAL_RECOMMENDATION",
        "MULTIPLE_POSSIBLE_STANDARDS",
        "EXPERT_REVIEW_REQUIRED",
        "INSUFFICIENT_INFORMATION",
    )
    # Ensure no JSON encoding or unicode crashes in decision trace
    assert isinstance(res["decision_trace"], list)
    assert len(res["decision_trace"]) > 0


def test_gujarati_query_safety(engine):
    """Verifies a Gujarati script query executes safely through all 14 pipeline stages."""
    gu_query = "11 કેવી ટ્રાન્સફોર્મર સપ્લાય ટેન્ડર"
    res = engine.recommend(gu_query)

    assert res is not None
    assert res["query"]["language"] == "gu"
    assert "decision_state" in res
    assert isinstance(res["decision_trace"], list)


def test_hinglish_cable_query_retrieval(engine):
    """Verifies code-mixed Hinglish query correctly retrieves candidates and detects hinglish."""
    hinglish_query = "Substation ke liye 11 kV grade XLPE underground power cable chahiye"
    res = engine.recommend(hinglish_query)

    assert res is not None
    assert res["query"]["language"] == "hinglish"
    # Should identify candidates containing IS 7098
    cands = [c.get("standard_designation") for c in res.get("candidate_recommendations", [])]
    assert any("7098" in str(c) for c in cands)


def test_multilingual_response_contract_integrity(engine):
    """Verifies the response structure includes language and unicode characters correctly."""
    query = "સબસ્ટેશન માટે 33 kV સ્વિચગિયર અને કંટ્રોલગિયર"
    res = engine.recommend(query)

    assert res["query"]["raw_text"] == query
    assert res["query"]["language"] == "gu"
    assert "provenance" in res
    assert res["provenance"]["dense_effective_mode"] is not None
