"""
Phase P1-D: Bounded LLM Integration & Anti-Hallucination Guardrails Tests
Verifies:
  1. Strict JSON schema validation against schemas/llm_extraction.schema.json (additionalProperties: false).
  2. Strict verbatim substring span verification (zero weak token overlap fallback).
  3. Rejection of hallucinated spans and invalid offsets.
  4. Explainer anti-hallucination guardrails: primary_recommendation = null NEVER claims "recommended standard".
  5. Designation fidelity & regulatory fidelity enforcement.
  6. 100% offline hermetic execution via deterministic mock & fallback.
"""

import json
import pytest
from pathlib import Path
from typing import Optional

from src.llm.provider import BaseLLMProvider, MockLLMProvider
from src.llm.structured_extractor import BoundedStructuredExtractor
from src.llm.explanation import ExplanationFacts, EvidenceGroundedExplainer
from src.recommendation.engine import StandSpecRecommendationEngine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = PROJECT_ROOT / "data" / "processed" / "standards_graph.json"


@pytest.fixture(scope="module")
def graph():
    if not GRAPH_PATH.exists():
        pytest.skip(f"Standards graph missing at {GRAPH_PATH}")
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def engine(graph):
    return StandSpecRecommendationEngine(standards_graph=graph, retriever_mode="hybrid_deterministic")


class ControlledMockProvider(BaseLLMProvider):
    """Configurable mock provider for testing LLM edge cases."""

    def __init__(self, response_text: str, is_available_val: bool = True):
        self.response_text = response_text
        self.available = is_available_val

    def generate(self, prompt: str, system_instruction: Optional[str] = None, json_mode: bool = False) -> str:
        return self.response_text

    def is_available(self) -> bool:
        return self.available


# ── TEST 1: Offline Deterministic Fallback when LLM Unavailable ──
def test_extractor_offline_fallback_when_unavailable():
    """When provider is unavailable, fallback gracefully with LLM_UNAVAILABLE mode."""
    extractor = BoundedStructuredExtractor(llm_provider=ControlledMockProvider("", is_available_val=False))
    query = "Supply of 110 mm HDPE pipes PE-100 PN 10 for drinking water distribution"
    result = extractor.extract(query)

    assert result["extractor_mode"] == "LLM_UNAVAILABLE"
    assert "requirements" in result
    assert result["requirements"].get("product") is not None
    assert "hdpe" in result["requirements"]["product"]["value"].lower()


# ── TEST 2: Valid Grounded LLM Extraction ──
def test_extractor_accepts_valid_grounded_spans():
    """Verbatim substring spans conforming to schema are accepted."""
    query = "Supply of 110 mm HDPE pipes PE-100 PN 10 for drinking water"
    # "HDPE pipes" is at index 17..27
    start_idx = query.find("HDPE pipes")
    end_idx = start_idx + len("HDPE pipes")

    valid_json = json.dumps({
        "product": {
            "value": "HDPE pipes",
            "evidence_text": "HDPE pipes",
            "start_char": start_idx,
            "end_char": end_idx,
            "confidence": 0.95
        },
        "material": {
            "value": "PE-100",
            "evidence_text": "PE-100",
            "start_char": query.find("PE-100"),
            "end_char": query.find("PE-100") + len("PE-100"),
            "confidence": 0.90
        }
    })

    provider = ControlledMockProvider(valid_json)
    extractor = BoundedStructuredExtractor(llm_provider=provider)
    result = extractor.extract(query)

    assert result["extractor_mode"] == "LLM_ASSISTED"
    assert result["requirements"]["product"]["value"] == "HDPE pipes"
    assert result["requirements"]["product"]["start_char"] == start_idx


# ── TEST 3: Strict Rejection of Hallucinated and Weak Token Spans ──
def test_extractor_rejects_hallucinated_and_weak_token_spans():
    """
    Substrings that do not exist verbatim in the query text MUST be rejected.
    Zero tolerance for weak token overlap.
    """
    query = "Supply of 110 mm high density polyethylene pipes"

    # Hallucinated extraction: "tubular conduit" (does not exist in query)
    # Weak token overlap: "polyethylene cables" (shares "polyethylene" but is not verbatim)
    hallucinated_json = json.dumps({
        "product": {
            "value": "polyethylene cables",
            "evidence_text": "polyethylene cables",
            "start_char": 0,
            "end_char": 19,
            "confidence": 0.90
        },
        "material": {
            "value": "tubular conduit",
            "evidence_text": "tubular conduit",
            "start_char": 0,
            "end_char": 15,
            "confidence": 0.80
        }
    })

    provider = ControlledMockProvider(hallucinated_json)
    extractor = BoundedStructuredExtractor(llm_provider=provider)
    grounded = extractor._verify_and_filter_grounding(query, json.loads(hallucinated_json))

    # Both ungrounded spans must be rejected
    assert "product" not in grounded
    assert "material" not in grounded


# ── TEST 4: Schema Violation Fallback ──
def test_extractor_rejects_additional_properties_schema_violation():
    """Violations of additionalProperties: false trigger DETERMINISTIC_FALLBACK."""
    query = "Supply of 110 mm HDPE pipes"
    illegal_extra_props_json = json.dumps({
        "product": "HDPE pipes",
        "hallucinated_attribute": "dangerous_injection",  # Not allowed by schema
    })

    provider = ControlledMockProvider(illegal_extra_props_json)
    extractor = BoundedStructuredExtractor(llm_provider=provider)
    result = extractor.extract(query)

    # Must fail schema validation and fallback gracefully
    assert result["extractor_mode"] == "DETERMINISTIC_FALLBACK"


# ── TEST 5: Explainer Rejects Recommendation Claim when Primary is Null ──
def test_explainer_rejects_recommendation_claim_when_primary_null():
    """When primary recommendation is null, LLM output claiming a recommended standard is rejected."""
    rec_result = {
        "decision_state": "NO_CONFIDENT_MATCH",
        "abstention_reason": "No candidate standard met evidentiary threshold",
        "primary_recommendation": None,
        "review_candidate": None,
    }

    facts = ExplanationFacts.from_recommendation_result(rec_result)
    assert facts.is_recommended is False

    # Hallucinating LLM claiming a recommended standard
    hallucinated_llm_text = "The recommended standard is IS 4984 for high density polyethylene pipes."
    explainer = EvidenceGroundedExplainer()

    # Must fail validation!
    assert explainer._validate_llm_response(hallucinated_llm_text, facts) is False

    # Complete explain() pipeline must safely fall back to deterministic explanation
    explainer_with_mock = EvidenceGroundedExplainer(llm_provider=ControlledMockProvider(hallucinated_llm_text))
    explanation = explainer_with_mock.explain(rec_result)

    assert "recommended standard" not in explanation.lower()
    assert "NO_CONFIDENT_MATCH" in explanation


# ── TEST 6: Explainer Rejects Altered Standard Designation ──
def test_explainer_rejects_altered_standard_designation():
    """LLM altering standard designation IS 4984 to IS 9999 is rejected."""
    rec_result = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "standard_designation": "IS 4984:2016",
            "title": "High Density Polyethylene Pipes",
            "applicability": {"matched_attributes": ["product", "material"]},
            "regulatory": {"regulatory_state": "MANDATORY_CONFIRMED", "qco_order_number": "DPIIT-QCO-PIPE-2023"},
            "lifecycle": {"recommended_edition": "IS 4984:2016"},
        }
    }
    facts = ExplanationFacts.from_recommendation_result(rec_result)
    assert facts.is_recommended is True

    # Hallucinated designation
    altered_llm_text = "For your procurement, we recommend IS 9999:2020 which is mandatory under DPIIT."
    explainer = EvidenceGroundedExplainer()

    assert explainer._validate_llm_response(altered_llm_text, facts) is False


# ── TEST 7: Explainer Rejects Regulatory Mandate Inventions ──
def test_explainer_rejects_regulatory_invention():
    """LLM claiming mandatory status for a voluntary standard is rejected."""
    rec_result = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "standard_designation": "IS 10810 (Part 53):1984",
            "title": "Methods of Test for Cables",
            "applicability": {"matched_attributes": ["product"]},
            "regulatory": {"regulatory_state": "VOLUNTARY_OR_UNLISTED"},
            "lifecycle": {"recommended_edition": "IS 10810 (Part 53):1984"},
        }
    }
    facts = ExplanationFacts.from_recommendation_result(rec_result)
    assert facts.regulatory_state == "VOLUNTARY_OR_UNLISTED"

    invented_qco_text = "Standard IS 10810 is mandatory under QCO gazette notification for cable testing."
    explainer = EvidenceGroundedExplainer()

    assert explainer._validate_llm_response(invented_qco_text, facts) is False


# ── TEST 8: Recommendation Engine Output Contains Grounded Explanation ──
def test_engine_output_contains_grounded_natural_language_explanation(engine):
    """RecommendationResult contains natural_language_explanation field grounded in facts."""
    query = "Supply of 110 mm HDPE pipes PE-100 PN 10 for drinking water distribution"
    result = engine.recommend(query)

    assert "natural_language_explanation" in result
    explanation = result["natural_language_explanation"]
    assert isinstance(explanation, str)
    assert len(explanation) > 10

    if result["primary_recommendation"]:
        assert "4984" in explanation
    else:
        assert "recommended standard" not in explanation.lower()
