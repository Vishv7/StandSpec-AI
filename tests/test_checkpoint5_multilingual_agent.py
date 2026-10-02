"""
Regression Tests for Checkpoint 5: Multilingual / Agent Layer
PS 26108 Phases 12-13.

Phase 12: Multilingual Query Normalization
Phase 13: Agent Orchestration Hardening
"""

import pytest
from src.extraction.multilingual_normalizer import (
    detect_language,
    transliterate_to_english,
    normalize_multilingual_query,
    NormalizationResult,
    TRANSLITERATION_MAP,
    DEVANAGARI_MAP,
    GUJARATI_MAP,
)
from src.agent.safety_invariants import (
    InvariantSeverity,
    InvariantViolation,
    InvariantCheckResult,
    check_designation_integrity,
    check_recommendation_grounding,
    check_claim_consistency,
    check_abstention_honesty,
    check_no_hallucination,
    validate_agent_response,
)


# ============================================================================
# Phase 12: Multilingual Query Normalization
# ============================================================================

class TestLanguageDetection:
    """Tests for language detection across Hindi, Gujarati, Hinglish, English."""

    def test_english_detection(self):
        result = detect_language("Supply of HDPE pipes for potable water distribution")
        assert result["detected"] == "en"
        assert result["confidence"] >= 0.90
        assert result["is_multilingual"] is False

    def test_hindi_detection(self):
        result = detect_language("पीने के पानी के लिए एचडीपीई पाइप की आपूर्ति")
        assert result["detected"] == "hi"
        assert result["confidence"] >= 0.90
        assert result["contains_hindi"] is True

    def test_gujarati_detection(self):
        result = detect_language("પીવાના પાણી માટે એચડીપીઇ પાઇપ")
        assert result["detected"] == "gu"
        assert result["contains_gujarati"] is True

    def test_hinglish_detection(self):
        result = detect_language("HDPE paani pipe chahiye peene ke liye")
        assert result["detected"] == "hinglish"
        assert result["contains_hinglish"] is True
        assert result["is_multilingual"] is True

    def test_is_multilingual_flag(self):
        """Non-English text must set is_multilingual flag."""
        hindi = detect_language("सीमेंट की आपूर्ति")
        assert hindi["is_multilingual"] is True

        english = detect_language("Supply of OPC cement grade 53")
        assert english["is_multilingual"] is False


class TestTransliteration:
    """Tests for transliteration from Hinglish/Hindi/Gujarati to English."""

    def test_hinglish_pipe_query(self):
        lang_meta = {"detected": "hinglish", "contains_hinglish": True, "is_multilingual": True}
        result, records = transliterate_to_english(
            "HDPE paani pipe chahiye peene ke liye", lang_meta
        )
        # Should transliterate paani → water, chahiye → required, etc.
        assert "water" in result.lower()
        assert len(records) > 0

    def test_devanagari_transliteration(self):
        lang_meta = {"detected": "hi", "contains_hindi": True, "is_multilingual": True}
        result, records = transliterate_to_english(
            "एचडीपीई पाइप", lang_meta
        )
        assert "HDPE" in result
        assert "pipe" in result.lower()
        assert len(records) > 0

    def test_gujarati_transliteration(self):
        lang_meta = {"detected": "gu", "contains_gujarati": True, "is_multilingual": True}
        result, records = transliterate_to_english(
            "એચડીપીઇ પાણી પુરવઠો", lang_meta
        )
        assert "HDPE" in result
        assert "water supply" in result.lower()

    def test_english_passthrough(self):
        """English text should pass through unchanged."""
        lang_meta = {"detected": "en", "is_multilingual": False}
        result, records = transliterate_to_english(
            "Supply of 11 kV XLPE power cable", lang_meta
        )
        assert result == "Supply of 11 kV XLPE power cable"
        assert len(records) == 0


class TestMultilingualNormalizationPipeline:
    """Tests for the full normalization pipeline."""

    def test_english_query_passthrough(self):
        result = normalize_multilingual_query("Supply of HDPE pipes for water supply")
        assert result.detected_language == "en"
        assert result.normalized_text == result.original_text
        assert result.normalization_confidence >= 0.95
        assert result.is_multilingual is False

    def test_hindi_query_normalization(self):
        result = normalize_multilingual_query("एचडीपीई पाइप पीने के पानी के लिए")
        assert result.detected_language == "hi"
        assert result.is_multilingual is True
        assert "HDPE" in result.normalized_text
        assert "pipe" in result.normalized_text.lower()
        assert len(result.transliterations_applied) > 0

    def test_hinglish_query_normalization(self):
        result = normalize_multilingual_query("bijli ka taar chahiye 11kV wala")
        assert result.detected_language == "hinglish"
        assert result.is_multilingual is True
        assert len(result.transliterations_applied) > 0

    def test_empty_query(self):
        result = normalize_multilingual_query("")
        assert result.detected_language == "en"
        assert result.normalized_text == ""
        assert result.normalization_confidence == 0.0

    def test_provenance_preserved(self):
        """Original text must always be preserved."""
        original = "sariya chahiye Fe 500D wala TMT"
        result = normalize_multilingual_query(original)
        assert result.original_text == original
        assert result.original_text != result.normalized_text or result.detected_language == "en"

    def test_result_to_dict(self):
        result = normalize_multilingual_query("Supply of HDPE pipes")
        d = result.to_dict()
        assert "original_text" in d
        assert "normalized_text" in d
        assert "detected_language" in d
        assert "is_multilingual" in d

    def test_copper_hindi(self):
        result = normalize_multilingual_query("तांबा तार 4 sq mm")
        assert "copper" in result.normalized_text.lower()

    def test_cement_hindi(self):
        result = normalize_multilingual_query("सीमेंट ग्रेड 53")
        assert "cement" in result.normalized_text.lower()


# ============================================================================
# Phase 13: Agent Safety Invariants
# ============================================================================

class TestDesignationIntegrity:
    """Tests for INV-1: Designation Integrity."""

    def test_valid_designation_passes(self):
        response = {
            "primary_recommendation": {"standard_designation": "IS 4984:2016"},
        }
        violations = check_designation_integrity(response, {"IS 4984:2016", "IS 7098"})
        assert len(violations) == 0

    def test_fabricated_designation_fails(self):
        response = {
            "primary_recommendation": {"standard_designation": "IS 99999:2099"},
        }
        violations = check_designation_integrity(response, {"IS 4984:2016", "IS 7098"})
        assert len(violations) > 0
        assert violations[0].severity == InvariantSeverity.CRITICAL

    def test_no_primary_passes(self):
        response = {"primary_recommendation": None}
        violations = check_designation_integrity(response, {"IS 4984:2016"})
        assert len(violations) == 0

    def test_base_number_match_passes(self):
        """Designation with different year but same base should pass."""
        response = {
            "primary_recommendation": {"standard_designation": "IS 4984:2022"},
        }
        violations = check_designation_integrity(response, {"IS 4984:2016"})
        assert len(violations) == 0


class TestRecommendationGrounding:
    """Tests for INV-2: Recommendation Grounding."""

    def test_grounded_primary_passes(self):
        response = {
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "primary_recommendation": {
                "standard_designation": "IS 4984:2016",
                "title": "HDPE Pipes",
                "applicability": {"matched_attributes": ["product"]},
            },
        }
        violations = check_recommendation_grounding(response)
        assert len(violations) == 0

    def test_ungrounded_primary_fails(self):
        response = {
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "primary_recommendation": {
                "standard_designation": "IS 4984:2016",
            },
        }
        violations = check_recommendation_grounding(response)
        assert any(v.invariant_id == "INV-2-GROUNDING-APPLICABILITY" for v in violations)


class TestClaimConsistency:
    """Tests for INV-3: Claim Consistency."""

    def test_valid_primary_claim(self):
        response = {
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "claim_level": "VERIFIED_FOR_RECOMMENDATION",
        }
        violations = check_claim_consistency(response)
        assert len(violations) == 0

    def test_overclaimed_abstention(self):
        """Abstention state with VERIFIED claim is a violation."""
        response = {
            "decision_state": "NO_CONFIDENT_MATCH",
            "claim_level": "VERIFIED_FOR_RECOMMENDATION",
        }
        violations = check_claim_consistency(response)
        assert len(violations) > 0
        assert violations[0].severity == InvariantSeverity.CRITICAL

    def test_downgraded_claim_passes(self):
        """Lower claim for a positive state is acceptable."""
        response = {
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "claim_level": "PLAUSIBLE",
        }
        violations = check_claim_consistency(response)
        assert len(violations) == 0


class TestAbstentionHonesty:
    """Tests for INV-5: Abstention Honesty."""

    def test_honest_abstention(self):
        response = {
            "decision_state": "NO_CONFIDENT_MATCH",
            "primary_recommendation": None,
        }
        violations = check_abstention_honesty(response)
        assert len(violations) == 0

    def test_dishonest_abstention_with_primary(self):
        """Abstention state WITH a primary recommendation is a violation."""
        response = {
            "decision_state": "INSUFFICIENT_INFORMATION",
            "primary_recommendation": {"standard_designation": "IS 4984:2016"},
        }
        violations = check_abstention_honesty(response)
        assert len(violations) > 0
        assert violations[0].severity == InvariantSeverity.CRITICAL

    def test_primary_state_without_recommendation(self):
        """Primary state WITHOUT a recommendation is a violation."""
        response = {
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "primary_recommendation": None,
        }
        violations = check_abstention_honesty(response)
        assert len(violations) > 0


class TestNoHallucination:
    """Tests for INV-7: No Hallucination."""

    def test_known_designation_passes(self):
        violations = check_no_hallucination(
            response={},
            llm_text="IS 4984 is the correct standard for HDPE pipes.",
            known_designations={"IS 4984:2016", "IS 7098 (Part 2):2011"},
        )
        assert len(violations) == 0

    def test_hallucinated_designation_fails(self):
        violations = check_no_hallucination(
            response={},
            llm_text="IS 88888 is the standard for unicorn cables.",
            known_designations={"IS 4984:2016"},
        )
        assert len(violations) > 0
        assert violations[0].severity == InvariantSeverity.CRITICAL

    def test_no_llm_text_passes(self):
        violations = check_no_hallucination(response={}, llm_text=None, known_designations=set())
        assert len(violations) == 0


class TestFullInvariantValidation:
    """Tests for the complete validate_agent_response pipeline."""

    def test_valid_response_passes(self):
        response = {
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "claim_level": "VERIFIED_FOR_RECOMMENDATION",
            "primary_recommendation": {
                "standard_designation": "IS 4984:2016",
                "title": "HDPE Pipes",
                "applicability": {"matched_attributes": ["product", "material"]},
            },
        }
        result = validate_agent_response(
            response,
            known_designations={"IS 4984:2016"},
        )
        assert result.is_valid is True
        assert result.critical_count == 0

    def test_invalid_response_fails(self):
        response = {
            "decision_state": "NO_CONFIDENT_MATCH",
            "claim_level": "VERIFIED_FOR_RECOMMENDATION",
            "primary_recommendation": {"standard_designation": "IS 99999"},
        }
        result = validate_agent_response(
            response,
            known_designations={"IS 4984:2016"},
        )
        assert result.is_valid is False
        assert result.critical_count > 0

    def test_invariant_check_result_structure(self):
        result = InvariantCheckResult(is_valid=True)
        result.add_violation(InvariantViolation(
            invariant_id="TEST",
            severity=InvariantSeverity.WARNING,
            message="Test warning",
        ))
        assert result.is_valid is True
        assert result.warning_count == 1

        result.add_violation(InvariantViolation(
            invariant_id="TEST-CRITICAL",
            severity=InvariantSeverity.CRITICAL,
            message="Test critical",
        ))
        assert result.is_valid is False
        assert result.critical_count == 1
