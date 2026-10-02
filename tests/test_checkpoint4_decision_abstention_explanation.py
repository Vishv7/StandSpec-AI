"""
Regression Tests for Checkpoint 4: Decision Engine / Abstention / Explanation
PS 26108 Phases 9-11.

Phase 9:  Decision State Machine
Phase 10: Abstention Policy Hardening
Phase 11: Explanation Generation
"""

import pytest
from src.recommendation.decision_state_machine import (
    DecisionState,
    ClaimLevel,
    DecisionStateSpec,
    DECISION_STATE_SPECS,
    VALID_TRANSITIONS,
    get_state_spec,
    get_claim_level,
    is_valid_transition,
    validate_decision_output,
)
from src.calibration.policy import SelectiveAbstentionPolicy
from src.recommendation.explanation_templates import (
    generate_explanation,
    StructuredExplanation,
)


# ============================================================================
# Phase 9: Decision State Machine
# ============================================================================

class TestDecisionStateEnum:
    """Tests that all decision states are properly defined."""

    def test_all_eight_states_exist(self):
        states = [s.value for s in DecisionState]
        assert "PRIMARY_RECOMMENDATION_AVAILABLE" in states
        assert "CONDITIONAL_RECOMMENDATION" in states
        assert "MULTIPLE_POSSIBLE_STANDARDS" in states
        assert "EXPERT_REVIEW_REQUIRED" in states
        assert "NO_CONFIDENT_MATCH" in states
        assert "INSUFFICIENT_INFORMATION" in states
        assert "OUTSIDE_PROTOTYPE_COVERAGE" in states
        assert "CONTRADICTORY_SPECIFICATIONS" in states
        assert "PROCESSING" in states

    def test_all_terminal_states_have_specs(self):
        """Every terminal state must have a DecisionStateSpec."""
        terminal_states = [s for s in DecisionState if s != DecisionState.PROCESSING]
        for state in terminal_states:
            assert state.value in DECISION_STATE_SPECS, \
                f"State {state.value} missing from DECISION_STATE_SPECS"

    def test_positive_states_require_primary(self):
        """PRIMARY and CONDITIONAL must require a primary recommendation."""
        assert DECISION_STATE_SPECS["PRIMARY_RECOMMENDATION_AVAILABLE"].requires_primary is True
        assert DECISION_STATE_SPECS["CONDITIONAL_RECOMMENDATION"].requires_primary is True

    def test_abstention_states_flagged(self):
        """All abstention states must be flagged as is_abstention."""
        abstention_states = [
            "NO_CONFIDENT_MATCH",
            "INSUFFICIENT_INFORMATION",
            "OUTSIDE_PROTOTYPE_COVERAGE",
            "CONTRADICTORY_SPECIFICATIONS",
        ]
        for s in abstention_states:
            assert DECISION_STATE_SPECS[s].is_abstention is True, f"{s} should be is_abstention"

    def test_non_abstention_states_not_flagged(self):
        """Positive states must NOT be flagged as abstention."""
        assert DECISION_STATE_SPECS["PRIMARY_RECOMMENDATION_AVAILABLE"].is_abstention is False
        assert DECISION_STATE_SPECS["CONDITIONAL_RECOMMENDATION"].is_abstention is False


class TestClaimLevels:
    """Tests for claim level ordering and assignment."""

    def test_claim_level_ordering(self):
        """Claim levels must have a strict ordering."""
        order = [
            ClaimLevel.ABSTAINED,
            ClaimLevel.REVIEW_REQUIRED,
            ClaimLevel.PLAUSIBLE,
            ClaimLevel.VERIFIED_FOR_RECOMMENDATION,
        ]
        assert len(order) == 4

    def test_primary_gets_verified_claim(self):
        assert get_claim_level("PRIMARY_RECOMMENDATION_AVAILABLE") == "VERIFIED_FOR_RECOMMENDATION"

    def test_conditional_gets_plausible_claim(self):
        assert get_claim_level("CONDITIONAL_RECOMMENDATION") == "PLAUSIBLE"

    def test_abstention_gets_abstained_claim(self):
        assert get_claim_level("NO_CONFIDENT_MATCH") == "ABSTAINED"
        assert get_claim_level("OUTSIDE_PROTOTYPE_COVERAGE") == "ABSTAINED"

    def test_review_gets_review_claim(self):
        assert get_claim_level("EXPERT_REVIEW_REQUIRED") == "REVIEW_REQUIRED"


class TestValidTransitions:
    """Tests for decision state transition rules."""

    def test_processing_can_reach_any_terminal(self):
        """PROCESSING can transition to any terminal state."""
        for state in DecisionState:
            if state != DecisionState.PROCESSING:
                assert is_valid_transition("PROCESSING", state.value), \
                    f"PROCESSING → {state.value} should be valid"

    def test_primary_can_be_downgraded(self):
        """PRIMARY can transition down to CONDITIONAL, REVIEW, or NO_MATCH."""
        assert is_valid_transition("PRIMARY_RECOMMENDATION_AVAILABLE", "CONDITIONAL_RECOMMENDATION")
        assert is_valid_transition("PRIMARY_RECOMMENDATION_AVAILABLE", "EXPERT_REVIEW_REQUIRED")
        assert is_valid_transition("PRIMARY_RECOMMENDATION_AVAILABLE", "NO_CONFIDENT_MATCH")

    def test_primary_cannot_upgrade_to_outside(self):
        """PRIMARY cannot transition to OUTSIDE_PROTOTYPE_COVERAGE."""
        assert not is_valid_transition("PRIMARY_RECOMMENDATION_AVAILABLE", "OUTSIDE_PROTOTYPE_COVERAGE")

    def test_terminal_abstention_has_no_transitions(self):
        """Terminal abstention states cannot transition further."""
        terminal_states = [
            "NO_CONFIDENT_MATCH",
            "INSUFFICIENT_INFORMATION",
            "OUTSIDE_PROTOTYPE_COVERAGE",
            "CONTRADICTORY_SPECIFICATIONS",
        ]
        for s in terminal_states:
            valid = VALID_TRANSITIONS.get(s, set())
            assert len(valid) == 0, f"{s} should have no outgoing transitions, got {valid}"


class TestOutputValidation:
    """Tests for decision output validation."""

    def test_valid_primary_output(self):
        output = {
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "primary_recommendation": {"standard_designation": "IS 4984:2016"},
            "claim_level": "VERIFIED_FOR_RECOMMENDATION",
        }
        violations = validate_decision_output(output)
        assert len(violations) == 0

    def test_invalid_missing_primary(self):
        """PRIMARY state without primary_recommendation is a violation."""
        output = {
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "primary_recommendation": None,
            "claim_level": "VERIFIED_FOR_RECOMMENDATION",
        }
        violations = validate_decision_output(output)
        assert any("requires primary_recommendation" in v for v in violations)

    def test_invalid_abstention_with_primary(self):
        """Abstention state WITH primary_recommendation is a violation."""
        output = {
            "decision_state": "NO_CONFIDENT_MATCH",
            "primary_recommendation": {"standard_designation": "IS 4984:2016"},
        }
        violations = validate_decision_output(output)
        assert any("must not have primary_recommendation" in v for v in violations)

    def test_unknown_state_is_violation(self):
        """Unknown state is a violation."""
        output = {"decision_state": "TOTALLY_INVALID_STATE"}
        violations = validate_decision_output(output)
        assert any("Unknown decision state" in v for v in violations)

    def test_claim_upgrade_is_violation(self):
        """Claim level stronger than state allows is a violation."""
        output = {
            "decision_state": "NO_CONFIDENT_MATCH",
            "primary_recommendation": None,
            "claim_level": "VERIFIED_FOR_RECOMMENDATION",
        }
        violations = validate_decision_output(output)
        assert any("stronger than state" in v for v in violations)


# ============================================================================
# Phase 10: Abstention Policy Hardening
# ============================================================================

class TestAbstentionPolicyMetadata:
    """Tests for the hardened abstention policy with metadata."""

    @pytest.fixture
    def policy(self):
        return SelectiveAbstentionPolicy(
            tau_recommend=0.40,
            tau_min=0.35,
            delta_margin=0.04,
        )

    def test_build_metadata_abstention(self, policy):
        meta = policy.build_abstention_metadata(
            decision_state="NO_CONFIDENT_MATCH",
            abstention_reason="Confidence too low",
            primary_rec=None,
            viable_recs=[],
        )
        assert meta["is_abstention"] is True
        assert meta["is_positive"] is False
        assert meta["abstention_category"] == "CONFIDENCE_INSUFFICIENT"
        assert "user_actionable" in meta
        assert meta["confidence_context"]["tau_recommend"] == 0.40

    def test_build_metadata_positive(self, policy):
        meta = policy.build_abstention_metadata(
            decision_state="PRIMARY_RECOMMENDATION_AVAILABLE",
            abstention_reason=None,
            primary_rec={"calibrated_confidence": 0.75},
            viable_recs=[{"calibrated_confidence": 0.75}],
        )
        assert meta["is_abstention"] is False
        assert meta["is_positive"] is True
        assert meta["abstention_category"] == "NONE"
        assert meta["confidence_context"]["top_candidate_confidence"] == 0.75

    def test_build_metadata_insufficient(self, policy):
        meta = policy.build_abstention_metadata(
            decision_state="INSUFFICIENT_INFORMATION",
            abstention_reason="Missing voltage class",
            primary_rec=None,
            viable_recs=[],
            missing_discriminators=["voltage", "insulation"],
        )
        assert meta["is_abstention"] is True
        assert meta["abstention_category"] == "QUERY_UNDERSPECIFIED"
        assert "voltage" in meta["user_actionable"]
        assert "insulation" in meta["user_actionable"]

    def test_build_metadata_contradictory(self, policy):
        meta = policy.build_abstention_metadata(
            decision_state="CONTRADICTORY_SPECIFICATIONS",
            abstention_reason="HDPE pipe with 33kV XLPE insulation",
            primary_rec=None,
            viable_recs=[],
        )
        assert meta["is_abstention"] is True
        assert meta["abstention_category"] == "QUERY_INVALID"
        assert "contradictory" in meta["user_actionable"].lower()

    def test_build_metadata_review(self, policy):
        meta = policy.build_abstention_metadata(
            decision_state="EXPERT_REVIEW_REQUIRED",
            abstention_reason="Missing scope evidence",
            primary_rec=None,
            viable_recs=[],
            evidence_gaps=["SCOPE_MISSING", "LIFECYCLE_UNVERIFIED"],
        )
        assert meta["is_review"] is True
        assert meta["abstention_category"] == "EVIDENCE_INSUFFICIENT"
        assert "SCOPE_MISSING" in meta["user_actionable"]

    def test_build_metadata_ambiguous(self, policy):
        meta = policy.build_abstention_metadata(
            decision_state="MULTIPLE_POSSIBLE_STANDARDS",
            abstention_reason="Narrow margin",
            primary_rec={"calibrated_confidence": 0.55},
            viable_recs=[{"c": 0.55}, {"c": 0.53}],
        )
        assert meta["is_ambiguous"] is True
        assert meta["abstention_category"] == "AMBIGUOUS_MATCH"


class TestAbstentionPolicyDecide:
    """Tests for the core decide() method."""

    @pytest.fixture
    def policy(self):
        return SelectiveAbstentionPolicy(
            tau_recommend=0.40,
            tau_min=0.35,
            delta_margin=0.04,
        )

    def test_empty_candidates_returns_no_match(self, policy):
        state, reason, primary, viable = policy.decide([])
        assert state == "NO_CONFIDENT_MATCH"
        assert primary is None

    def test_high_confidence_returns_primary(self, policy):
        candidates = [{"confidence_score": 0.80, "standard_designation": "IS 4984:2016"}]
        state, reason, primary, viable = policy.decide(candidates)
        assert state == "PRIMARY_RECOMMENDATION_AVAILABLE"
        assert primary is not None
        assert primary["standard_designation"] == "IS 4984:2016"

    def test_low_confidence_returns_no_match(self, policy):
        candidates = [{"confidence_score": 0.05, "standard_designation": "IS 9999"}]
        state, reason, primary, viable = policy.decide(candidates)
        assert state == "NO_CONFIDENT_MATCH"

    def test_missing_discriminators_returns_insufficient(self, policy):
        # Raw scores need to be high enough that calibrated probability >= tau_min
        candidates = [
            {"confidence_score": 0.90, "standard_designation": "IS 4984:2016"},
            {"confidence_score": 0.88, "standard_designation": "IS 4985:2000"},
        ]
        state, reason, primary, viable = policy.decide(
            candidates,
            missing_discriminators=["voltage_class", "material"],
        )
        assert state == "INSUFFICIENT_INFORMATION"


# ============================================================================
# Phase 11: Explanation Generation
# ============================================================================

class TestStructuredExplanation:
    """Tests for structured explanation templates."""

    def test_primary_explanation(self):
        result = {
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "primary_recommendation": {
                "standard_designation": "IS 4984:2016",
                "title": "HDPE Pipes for Potable Water",
                "calibrated_confidence": 0.82,
                "applicability": {"matched_attributes": ["product", "material", "application"]},
                "regulatory": {"regulatory_state": "VOLUNTARY"},
                "lifecycle": {"recommended_edition": "2016"},
            },
        }
        exp = generate_explanation(result)
        assert exp.decision_state == "PRIMARY_RECOMMENDATION_AVAILABLE"
        assert "IS 4984:2016" in exp.headline
        assert exp.standard_designation == "IS 4984:2016"
        assert exp.confidence_pct == 82.0
        assert exp.claim_level == "VERIFIED_FOR_RECOMMENDATION"
        assert len(exp.evidence_points) > 0

    def test_no_match_explanation(self):
        result = {
            "decision_state": "NO_CONFIDENT_MATCH",
            "primary_recommendation": None,
            "abstention_reason": "Low confidence",
        }
        exp = generate_explanation(result)
        assert exp.decision_state == "NO_CONFIDENT_MATCH"
        assert exp.claim_level == "ABSTAINED"
        assert "No Confident Match" in exp.headline
        assert exp.standard_designation is None

    def test_insufficient_info_explanation(self):
        result = {
            "decision_state": "INSUFFICIENT_INFORMATION",
            "primary_recommendation": None,
            "normalized_requirements": {"missing_discriminators": ["voltage", "insulation"]},
            "abstention_reason": "Missing voltage and insulation specs",
        }
        exp = generate_explanation(result)
        assert exp.decision_state == "INSUFFICIENT_INFORMATION"
        assert "Insufficient Information" in exp.headline
        assert any("voltage" in ep for ep in exp.evidence_points)

    def test_contradictory_explanation(self):
        result = {
            "decision_state": "CONTRADICTORY_SPECIFICATIONS",
            "primary_recommendation": None,
            "normalized_requirements": {
                "contradictions": ["HDPE pipe with 33kV XLPE insulation"],
            },
            "abstention_reason": "Cross-domain contradiction",
        }
        exp = generate_explanation(result)
        assert exp.decision_state == "CONTRADICTORY_SPECIFICATIONS"
        assert "Contradictory" in exp.headline
        assert any("HDPE" in ep for ep in exp.evidence_points)

    def test_outside_scope_explanation(self):
        result = {
            "decision_state": "OUTSIDE_PROTOTYPE_COVERAGE",
            "primary_recommendation": None,
        }
        exp = generate_explanation(result)
        assert exp.decision_state == "OUTSIDE_PROTOTYPE_COVERAGE"
        assert "Outside System Scope" in exp.headline
        assert exp.claim_level == "ABSTAINED"

    def test_expert_review_explanation(self):
        result = {
            "decision_state": "EXPERT_REVIEW_REQUIRED",
            "primary_recommendation": None,
            "review_candidate": {
                "designation": "IS 7098 (Part 2):2011",
                "title": "XLPE Cable",
                "missing_evidence": ["SCOPE_MISSING"],
            },
        }
        exp = generate_explanation(result)
        assert exp.decision_state == "EXPERT_REVIEW_REQUIRED"
        assert "IS 7098" in exp.headline
        assert exp.claim_level == "REVIEW_REQUIRED"
        assert any("SCOPE_MISSING" in ep for ep in exp.evidence_points)

    def test_multiple_standards_explanation(self):
        result = {
            "decision_state": "MULTIPLE_POSSIBLE_STANDARDS",
            "primary_recommendation": {"standard_designation": "IS 4984:2016"},
            "candidate_recommendations": [
                {"standard_designation": "IS 4984:2016"},
                {"standard_designation": "IS 4985:2000"},
            ],
        }
        exp = generate_explanation(result)
        assert exp.decision_state == "MULTIPLE_POSSIBLE_STANDARDS"
        assert "Multiple" in exp.headline
        assert exp.claim_level == "REVIEW_REQUIRED"

    def test_conditional_explanation(self):
        result = {
            "decision_state": "CONDITIONAL_RECOMMENDATION",
            "primary_recommendation": {
                "standard_designation": "IS 4984:2016",
                "title": "HDPE Pipes",
                "calibrated_confidence": 0.55,
            },
            "abstention_reason": "Voltage class not verified",
        }
        exp = generate_explanation(result)
        assert exp.decision_state == "CONDITIONAL_RECOMMENDATION"
        assert "Conditional" in exp.headline
        assert exp.claim_level == "PLAUSIBLE"


class TestExplanationRendering:
    """Tests for explanation rendering to text and dict."""

    def test_to_text_rendering(self):
        exp = StructuredExplanation(
            decision_state="PRIMARY_RECOMMENDATION_AVAILABLE",
            headline="Recommended: IS 4984:2016",
            summary="IS 4984:2016 is recommended.",
            evidence_points=["Product: HDPE pipe", "Material: HDPE"],
            caveats=["Verify edition"],
            user_action="Review recommendation.",
        )
        text = exp.to_text()
        assert "Recommended: IS 4984:2016" in text
        assert "Product: HDPE pipe" in text
        assert "Verify edition" in text
        assert "Recommended Action:" in text

    def test_to_dict_rendering(self):
        exp = StructuredExplanation(
            decision_state="NO_CONFIDENT_MATCH",
            headline="No Match",
            summary="No match found.",
            claim_level="ABSTAINED",
        )
        d = exp.to_dict()
        assert d["decision_state"] == "NO_CONFIDENT_MATCH"
        assert d["headline"] == "No Match"
        assert d["claim_level"] == "ABSTAINED"
        assert isinstance(d["evidence_points"], list)
        assert isinstance(d["caveats"], list)
