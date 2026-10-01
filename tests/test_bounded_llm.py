"""
Tests for Bounded Optional LLM Integration Module — StandSpec AI
Verifies that:
1. Systems operate 100% deterministically when no API key or provider is present.
2. Structured extraction output conforms to requirement schema.
3. Hallucinations that swap designations or misstate regulatory mandates are rejected.
"""

import json
import pytest
from src.llm.provider import MockLLMProvider, BoundedExternalLLMProvider
from src.llm.structured_extractor import BoundedStructuredExtractor
from src.llm.explanation import EvidenceGroundedExplainer


def test_offline_fallback_no_provider():
    """Verify that when no provider is supplied, deterministic extraction and explanation operate seamlessly."""
    extractor = BoundedStructuredExtractor(llm_provider=None)
    res = extractor.extract("Supply of 11 kV XLPE insulated underground power cables.")
    assert "requirements" in res
    assert res["requirements"]["product"]["normalization"] == "Power Cable"

    explainer = EvidenceGroundedExplainer(llm_provider=None)
    mock_rec = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "standard_designation": "IS 7098 (Part 2):2011",
            "title": "Crosslinked Polyethylene Insulated Cables",
            "regulatory": {
                "regulatory_state": "MANDATORY_CONFIRMED",
                "qco_order_number": "S.O. 3716(E)",
            },
            "applicability": {"matched_attributes": ["voltage", "material"]},
        },
    }
    explanation = explainer.explain(mock_rec)
    assert "IS 7098 (Part 2):2011" in explanation
    assert "MANDATORY under Gazette Order S.O. 3716(E)" in explanation


def test_mock_provider_structured_extraction():
    """Verify that mock LLM provider extracts valid structured JSON."""
    canned = {
        "Tender Clause": json.dumps({
            "product": "XLPE Power Cable",
            "material": "Crosslinked Polyethylene",
            "voltage": "11 kV",
            "domain": "ELECTROTECHNICAL",
        })
    }
    mock_llm = MockLLMProvider(canned_responses=canned)
    extractor = BoundedStructuredExtractor(llm_provider=mock_llm)
    res = extractor.extract("Supply of 11 kV XLPE insulated power cables.")
    assert res.get("extractor_mode") == "LLM_ASSISTED"
    assert "requirements" in res


def test_malformed_llm_json_fallback():
    """Verify that malformed LLM responses safely fallback to deterministic extraction."""
    canned = {"Tender Clause": "THIS IS NOT VALID JSON AT ALL {[[["}
    mock_llm = MockLLMProvider(canned_responses=canned)
    extractor = BoundedStructuredExtractor(llm_provider=mock_llm)
    res = extractor.extract("Supply of 11 kV XLPE insulated power cables.")
    assert res.get("extractor_mode") == "DETERMINISTIC_FALLBACK"
    assert res["requirements"]["product"]["normalization"] == "Power Cable"


def test_anti_hallucination_designation_safeguard():
    """Verify that if LLM swaps or omits the target designation, the explanation is rejected."""
    # LLM hallucinates IS 694 instead of the actual recommendation IS 7098
    hallucinated_response = "We recommend IS 694 for your low voltage needs."
    mock_llm = MockLLMProvider(canned_responses={"Summarize": hallucinated_response})
    explainer = EvidenceGroundedExplainer(llm_provider=mock_llm)

    mock_rec = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "standard_designation": "IS 7098 (Part 2):2011",
            "title": "Crosslinked Polyethylene Insulated Cables",
            "regulatory": {
                "regulatory_state": "MANDATORY_CONFIRMED",
                "qco_order_number": "S.O. 3716(E)",
            },
            "applicability": {"matched_attributes": ["voltage"]},
        },
    }

    explanation = explainer.explain(mock_rec)
    # The hallucinated text must be rejected in favor of the deterministic ground truth
    assert "IS 7098 (Part 2):2011" in explanation
    assert "IS 694" not in explanation


def test_anti_hallucination_regulatory_safeguard():
    """Verify that if LLM claims a mandatory standard is voluntary, it is rejected."""
    hallucinated_response = "IS 7098 (Part 2):2011 is completely voluntary with no government mandate."
    mock_llm = MockLLMProvider(canned_responses={"Summarize": hallucinated_response})
    explainer = EvidenceGroundedExplainer(llm_provider=mock_llm)

    mock_rec = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "standard_designation": "IS 7098 (Part 2):2011",
            "title": "Crosslinked Polyethylene Insulated Cables",
            "regulatory": {
                "regulatory_state": "MANDATORY_CONFIRMED",
                "qco_order_number": "S.O. 3716(E)",
            },
            "applicability": {"matched_attributes": ["voltage"]},
        },
    }

    explanation = explainer.explain(mock_rec)
    # Must reject the false "voluntary" statement and retain the mandatory gazette citation
    assert "MANDATORY under Gazette Order S.O. 3716(E)" in explanation
    assert "voluntary" not in explanation.lower()


def test_gemini_provider_environment_configuration(monkeypatch):
    """Verify GeminiLLMProvider behavior under environment variables."""
    from src.llm.provider import GeminiLLMProvider, get_llm_provider

    # 1. Disabled by default
    monkeypatch.delenv("STANDSPEC_LLM_ENABLED", raising=False)
    monkeypatch.delenv("STANDSPEC_LLM_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider = GeminiLLMProvider()
    assert not provider.is_available()

    with pytest.raises(RuntimeError, match="unavailable"):
        provider.generate("test prompt")

    # 2. Enabled without key
    monkeypatch.setenv("STANDSPEC_LLM_ENABLED", "true")
    provider_no_key = GeminiLLMProvider()
    assert not provider_no_key.is_available()

    # 3. Enabled with key
    monkeypatch.setenv("STANDSPEC_LLM_API_KEY", "test-api-key-12345")
    provider_with_key = GeminiLLMProvider()
    assert provider_with_key.is_available()

    # Factory should return GeminiLLMProvider
    monkeypatch.setenv("STANDSPEC_LLM_PROVIDER", "gemini")
    factory_provider = get_llm_provider()
    assert isinstance(factory_provider, GeminiLLMProvider)


def test_grounded_extractor_rejects_hallucinated_spans():
    """Verify that structured extractor rejects spans not present in query text."""
    query = "Supply of 11 kV XLPE insulated power cables."
    canned = {
        "Tender Clause": json.dumps({
            "product": {
                "value": "XLPE Power Cable",
                "evidence_text": "XLPE",
                "start_char": 16,
                "end_char": 20,
                "confidence": 0.95,
            },
            # Hallucinated material completely absent from query!
            "material": {
                "value": "Titanium Alloy Sheath",
                "evidence_text": "Titanium Alloy Sheath",
                "start_char": 0,
                "end_char": 21,
                "confidence": 0.99,
            },
        })
    }
    mock_llm = MockLLMProvider(canned_responses=canned)
    extractor = BoundedStructuredExtractor(llm_provider=mock_llm)
    res = extractor.extract(query)

    assert res.get("extractor_mode") == "LLM_ASSISTED"
    # Grounded product is present
    assert res["requirements"]["product"] is not None
    # Hallucinated titanium alloy must be rejected and not set
    assert res["requirements"].get("material") is None or "titanium" not in res["requirements"]["material"]["value"].lower()


def test_null_primary_anti_hallucination():
    """Verify that when primary recommendation is null, LLM cannot say 'recommended standard'."""
    from src.llm.explanation import ExplanationFacts

    rec_result = {
        "decision_state": "REVIEW_REQUIRED",
        "primary_recommendation": None,
        "abstention_reason": "Candidate standard is under review.",
        "review_candidate": {
            "standard_designation": "IS 16444 (Part 1):2015",
            "evidence_gaps": ["LIFECYCLE_UNVERIFIED"],
        },
    }

    facts = ExplanationFacts.from_recommendation_result(rec_result)
    assert not facts.is_recommended
    assert "LIFECYCLE_UNVERIFIED" in facts.evidence_gaps

    # LLM incorrectly tries to recommend the standard
    hallucinated = "The recommended standard for your smart meter tender is IS 16444 (Part 1):2015."
    mock_llm = MockLLMProvider(canned_responses={"Verified Facts": hallucinated})
    explainer = EvidenceGroundedExplainer(llm_provider=mock_llm)

    summary = explainer.explain(rec_result)
    # The hallucination saying "recommended standard" must be rejected
    assert "recommended standard" not in summary.lower()
    assert "REVIEW_REQUIRED" in summary
    assert "LIFECYCLE_UNVERIFIED" in summary


@pytest.mark.llm_live
def test_live_gemini_api_call():
    """Opt-in live integration test. Skipped unless explicitly enabled with real credentials."""
    import os
    if not os.environ.get("STANDSPEC_LLM_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("No live Gemini API key provided. Skipping live API test.")

    from src.llm.provider import GeminiLLMProvider
    provider = GeminiLLMProvider()
    if not provider.is_available():
        pytest.skip("Gemini provider not enabled in environment.")

    try:
        resp = provider.generate("Respond with the exact word 'PONG'.")
        assert "PONG" in resp
    except RuntimeError as e:
        err = str(e).lower()
        if "429" in err or "quota" in err or "rate" in err or "resourceexhausted" in err or "network access detected" in err:
            pytest.skip(f"Live Gemini API call skipped: {e}")
        raise

