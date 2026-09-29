"""
Tests for LLM Production Hardening — StandSpec AI (Phase P1-E Group P3).
Verifies:
1. DisabledLLMProvider reports is_available() == False and reason == "LLM_DISABLED".
2. BoundedStructuredExtractor supports explicit execution modes (DETERMINISTIC_ONLY, LLM_DISABLED_FALLBACK, etc.).
3. extract_to_open_world_query produces a compliant OpenWorldQuery contract.
4. Explainer strictly prohibits false claims of non-mandatory status when regulatory status is unverified or conflicting.
5. Explainer validates regulatory citations and rejects hallucinated S.O. numbers.
"""

import json
import pytest

from src.llm.provider import (
    BaseLLMProvider,
    MockLLMProvider,
    DisabledLLMProvider,
    GeminiLLMProvider,
    get_llm_provider,
)
from src.llm.structured_extractor import BoundedStructuredExtractor
from src.llm.explanation import ExplanationFacts, EvidenceGroundedExplainer
from src.query.open_world_contract import OpenWorldQuery


def test_disabled_llm_provider_contract(monkeypatch):
    """DisabledLLMProvider must report is_available() == False and raise on generate()."""
    provider = DisabledLLMProvider()
    assert not provider.is_available()
    assert provider.reason == "LLM_DISABLED"

    with pytest.raises(RuntimeError, match="LLM provider is disabled"):
        provider.generate("test prompt")

    # When STANDSPEC_LLM_ENABLED is not set, get_llm_provider() must return DisabledLLMProvider
    monkeypatch.delenv("STANDSPEC_LLM_ENABLED", raising=False)
    monkeypatch.delenv("STANDSPEC_LLM_PROVIDER", raising=False)
    default_provider = get_llm_provider()
    assert isinstance(default_provider, DisabledLLMProvider)
    assert not default_provider.is_available()


def test_extractor_execution_modes():
    """Verify BoundedStructuredExtractor explicit execution modes."""
    extractor = BoundedStructuredExtractor(llm_provider=None)
    query = "Supply of 33 kV XLPE insulated aluminium conductor power cable"

    # 1. DETERMINISTIC_ONLY mode
    res_det = extractor.extract(query, mode="DETERMINISTIC_ONLY")
    assert res_det["extractor_mode"] == "DETERMINISTIC_ONLY"
    assert res_det["requirements"]["product"]["value"] is not None

    # 2. LLM_DISABLED_FALLBACK with DisabledLLMProvider
    disabled_extractor = BoundedStructuredExtractor(llm_provider=DisabledLLMProvider())
    res_disabled = disabled_extractor.extract(query)
    assert res_disabled["extractor_mode"] == "LLM_DISABLED_FALLBACK"

    # 3. LLM_PROVIDER_UNAVAILABLE mode
    class UnavailProvider(BaseLLMProvider):
        def generate(self, prompt, **kwargs):
            return ""
        def is_available(self):
            return False

    unavail_extractor = BoundedStructuredExtractor(llm_provider=UnavailProvider())
    res_unavail = unavail_extractor.extract(query, mode="LLM_PROVIDER_UNAVAILABLE")
    assert res_unavail["extractor_mode"] == "LLM_PROVIDER_UNAVAILABLE"

    # 4. LLM_ERROR_FALLBACK mode
    class CrashingProvider(BaseLLMProvider):
        def generate(self, prompt, **kwargs):
            raise ConnectionResetError("Remote API dropped connection")
        def is_available(self):
            return True

    crash_extractor = BoundedStructuredExtractor(llm_provider=CrashingProvider())
    res_err = crash_extractor.extract(query, mode="LLM_ERROR_FALLBACK")
    assert res_err["extractor_mode"] == "LLM_ERROR_FALLBACK"


def test_extractor_reconciles_to_open_world_query():
    """extract_to_open_world_query must return a compliant OpenWorldQuery without leakage."""
    extractor = BoundedStructuredExtractor(llm_provider=DisabledLLMProvider())
    query_text = "Procurement of 53 grade ordinary Portland cement for structural bridge piers"

    ow_query = extractor.extract_to_open_world_query(query_text, query_id="Q_TENDER_099")
    assert isinstance(ow_query, OpenWorldQuery)
    assert ow_query.raw_text == query_text
    assert ow_query.procurement_object is not None
    assert ow_query.is_searchable is True
    assert ow_query.metadata.get("query_id") == "Q_TENDER_099"
    assert ow_query.metadata.get("extractor_mode") == "LLM_DISABLED_FALLBACK"

    # Ensure no benchmark keys leak
    ow_dict = ow_query.to_dict()
    assert "gold_standards" not in ow_dict
    assert "benchmark_id" not in ow_dict


def test_explainer_unverified_regulatory_safety():
    """When regulatory state is NOT_VERIFIED_IN_CURRENT_CORPUS, never say 'not mandatory'."""
    facts = ExplanationFacts(
        decision_state="PRIMARY_RECOMMENDATION_AVAILABLE",
        is_recommended=True,
        standard_designation="IS 1234:2020",
        title="Sample Test Standard",
        matched_attributes=["product"],
        regulatory_state="NOT_VERIFIED_IN_CURRENT_CORPUS",
    )

    explainer = EvidenceGroundedExplainer()
    explanation = explainer._generate_deterministic_explanation(facts)

    assert "Regulatory mandatory status was not verified in the current regulatory corpus" in explanation
    assert "not mandatory" not in explanation.lower()
    assert "voluntary" not in explanation.lower()

    # Rejection of LLM claiming "not mandatory" when status is unverified
    hallucinated_llm = "IS 1234:2020 is not mandatory and voluntary under current Indian rules."
    assert explainer._validate_llm_response(hallucinated_llm, facts) is False


def test_explainer_conflicting_regulatory_safety():
    """When regulatory state is CONFLICTING_EVIDENCE, explainer states conflicting evidence."""
    facts = ExplanationFacts(
        decision_state="PRIMARY_RECOMMENDATION_AVAILABLE",
        is_recommended=True,
        standard_designation="IS 5678:2018",
        title="Sample Conflicted Standard",
        regulatory_state="CONFLICTING_EVIDENCE",
    )

    explainer = EvidenceGroundedExplainer()
    explanation = explainer._generate_deterministic_explanation(facts)

    assert "Conflicting regulatory evidence prevents a verified mandate conclusion" in explanation

    # Rejection of LLM claiming definitive voluntary or mandatory status
    hallucinated_llm = "IS 5678:2018 is voluntary with no mandate."
    assert explainer._validate_llm_response(hallucinated_llm, facts) is False


def test_explainer_rejects_hallucinated_order_number():
    """LLM hallucinating an S.O. number not in evidence facts must be rejected."""
    facts = ExplanationFacts(
        decision_state="PRIMARY_RECOMMENDATION_AVAILABLE",
        is_recommended=True,
        standard_designation="IS 694:2010",
        title="PVC Insulated Cables",
        regulatory_state="MANDATORY_CONFIRMED",
        qco_order_number="S.O. 3716(E)",
    )

    explainer = EvidenceGroundedExplainer()

    valid_llm = "Standard IS 694:2010 is mandatory under S.O. 3716(E) for power cables."
    assert explainer._validate_llm_response(valid_llm, facts) is True

    # Hallucinated order number 9999(E)
    hallucinated_order_llm = "Standard IS 694:2010 is mandatory under S.O. 9999(E) for power cables."
    assert explainer._validate_llm_response(hallucinated_order_llm, facts) is False
