"""
Decision State Machine — StandSpec AI (Phase 9, Checkpoint 4)
PS 26108 §11: Formalized decision state machine with explicit transitions.

Defines every valid decision state, its meaning, allowable transitions,
and the evidence requirements for each state. This is the single source
of truth for what states the engine can produce and what they mean.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field


class DecisionState(str, Enum):
    """
    All valid terminal decision states in StandSpec AI.
    Every engine output MUST use one of these states.
    """
    # ── Positive outcomes ──
    PRIMARY_RECOMMENDATION_AVAILABLE = "PRIMARY_RECOMMENDATION_AVAILABLE"
    CONDITIONAL_RECOMMENDATION = "CONDITIONAL_RECOMMENDATION"

    # ── Ambiguity outcomes ──
    MULTIPLE_POSSIBLE_STANDARDS = "MULTIPLE_POSSIBLE_STANDARDS"
    EXPERT_REVIEW_REQUIRED = "EXPERT_REVIEW_REQUIRED"

    # ── Abstention outcomes ──
    NO_CONFIDENT_MATCH = "NO_CONFIDENT_MATCH"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    OUTSIDE_PROTOTYPE_COVERAGE = "OUTSIDE_PROTOTYPE_COVERAGE"
    CONTRADICTORY_SPECIFICATIONS = "CONTRADICTORY_SPECIFICATIONS"

    # ── Diagnostic states (intermediate, never terminal) ──
    PROCESSING = "PROCESSING"


class ClaimLevel(str, Enum):
    """
    Claim levels define the strength of the system's output assertion.
    They are monotonically ordered: higher levels require stronger evidence.
    """
    ABSTAINED = "ABSTAINED"                          # System chose not to recommend
    REVIEW_REQUIRED = "REVIEW_REQUIRED"              # Candidate identified but needs human review
    PLAUSIBLE = "PLAUSIBLE"                          # Likely correct but evidence gaps exist
    VERIFIED_FOR_RECOMMENDATION = "VERIFIED_FOR_RECOMMENDATION"  # All evidence gates passed


# ── Decision State Metadata ──
# Each state defines: description, required evidence, claim level, is_terminal

@dataclass
class DecisionStateSpec:
    """Specification for a decision state."""
    state: DecisionState
    description: str
    claim_level: ClaimLevel
    is_terminal: bool = True
    requires_primary: bool = False
    requires_review_candidate: bool = False
    is_abstention: bool = False
    required_evidence: List[str] = field(default_factory=list)
    user_action_required: str = ""


DECISION_STATE_SPECS: Dict[str, DecisionStateSpec] = {
    DecisionState.PRIMARY_RECOMMENDATION_AVAILABLE.value: DecisionStateSpec(
        state=DecisionState.PRIMARY_RECOMMENDATION_AVAILABLE,
        description="A primary standard recommendation is available with verified evidence across all gates.",
        claim_level=ClaimLevel.VERIFIED_FOR_RECOMMENDATION,
        requires_primary=True,
        required_evidence=["scope_ready", "applicability_ready", "lifecycle_ready", "provenance_ready"],
        user_action_required="Review the recommendation and verify against specific tender requirements.",
    ),
    DecisionState.CONDITIONAL_RECOMMENDATION.value: DecisionStateSpec(
        state=DecisionState.CONDITIONAL_RECOMMENDATION,
        description="A recommendation is available but with conditions — some technical parameters are unverified or unknown.",
        claim_level=ClaimLevel.PLAUSIBLE,
        requires_primary=True,
        required_evidence=["scope_ready", "applicability_ready"],
        user_action_required="Verify the unconfirmed conditions before final procurement decision.",
    ),
    DecisionState.MULTIPLE_POSSIBLE_STANDARDS.value: DecisionStateSpec(
        state=DecisionState.MULTIPLE_POSSIBLE_STANDARDS,
        description="Multiple standards match the query with similar confidence. Additional discriminators needed.",
        claim_level=ClaimLevel.REVIEW_REQUIRED,
        requires_primary=True,
        is_abstention=False,
        user_action_required="Provide additional technical specifications to disambiguate.",
    ),
    DecisionState.EXPERT_REVIEW_REQUIRED.value: DecisionStateSpec(
        state=DecisionState.EXPERT_REVIEW_REQUIRED,
        description="A plausible candidate was identified but lacks sufficient verified evidence for automated recommendation.",
        claim_level=ClaimLevel.REVIEW_REQUIRED,
        requires_review_candidate=True,
        user_action_required="Expert review required. Consult the identified review candidate against tender requirements.",
    ),
    DecisionState.NO_CONFIDENT_MATCH.value: DecisionStateSpec(
        state=DecisionState.NO_CONFIDENT_MATCH,
        description="No candidate standard achieved sufficient confidence for recommendation.",
        claim_level=ClaimLevel.ABSTAINED,
        is_abstention=True,
        user_action_required="Refine the query or consult domain experts for manual standard identification.",
    ),
    DecisionState.INSUFFICIENT_INFORMATION.value: DecisionStateSpec(
        state=DecisionState.INSUFFICIENT_INFORMATION,
        description="The procurement query lacks critical discriminating information needed for an unambiguous recommendation.",
        claim_level=ClaimLevel.ABSTAINED,
        is_abstention=True,
        user_action_required="Provide missing discriminators (material, voltage, grade, application, etc.).",
    ),
    DecisionState.OUTSIDE_PROTOTYPE_COVERAGE.value: DecisionStateSpec(
        state=DecisionState.OUTSIDE_PROTOTYPE_COVERAGE,
        description="The query specifies products outside the prototype coverage boundary (CED + ETD).",
        claim_level=ClaimLevel.ABSTAINED,
        is_abstention=True,
        user_action_required="This query is outside the current system scope. Consult BIS directly.",
    ),
    DecisionState.CONTRADICTORY_SPECIFICATIONS.value: DecisionStateSpec(
        state=DecisionState.CONTRADICTORY_SPECIFICATIONS,
        description="The procurement query contains contradictory technical specifications that cannot be simultaneously satisfied.",
        claim_level=ClaimLevel.ABSTAINED,
        is_abstention=True,
        user_action_required="Resolve the contradictions in the procurement specification before searching.",
    ),
}


# ── Valid Transitions ──
# Defines which states can transition to which other states.
# Used for invariant checking in the engine.

VALID_TRANSITIONS: Dict[str, Set[str]] = {
    DecisionState.PROCESSING.value: {
        DecisionState.PRIMARY_RECOMMENDATION_AVAILABLE.value,
        DecisionState.CONDITIONAL_RECOMMENDATION.value,
        DecisionState.MULTIPLE_POSSIBLE_STANDARDS.value,
        DecisionState.EXPERT_REVIEW_REQUIRED.value,
        DecisionState.NO_CONFIDENT_MATCH.value,
        DecisionState.INSUFFICIENT_INFORMATION.value,
        DecisionState.OUTSIDE_PROTOTYPE_COVERAGE.value,
        DecisionState.CONTRADICTORY_SPECIFICATIONS.value,
    },
    # PRIMARY can be downgraded if evidence check fails
    DecisionState.PRIMARY_RECOMMENDATION_AVAILABLE.value: {
        DecisionState.CONDITIONAL_RECOMMENDATION.value,
        DecisionState.EXPERT_REVIEW_REQUIRED.value,
        DecisionState.NO_CONFIDENT_MATCH.value,
    },
    # CONDITIONAL can be downgraded if further checks fail
    DecisionState.CONDITIONAL_RECOMMENDATION.value: {
        DecisionState.EXPERT_REVIEW_REQUIRED.value,
        DecisionState.NO_CONFIDENT_MATCH.value,
    },
    # MULTIPLE can be resolved or further downgraded
    DecisionState.MULTIPLE_POSSIBLE_STANDARDS.value: {
        DecisionState.PRIMARY_RECOMMENDATION_AVAILABLE.value,
        DecisionState.EXPERT_REVIEW_REQUIRED.value,
        DecisionState.NO_CONFIDENT_MATCH.value,
    },
    # Terminal abstention states cannot transition further
    DecisionState.NO_CONFIDENT_MATCH.value: set(),
    DecisionState.INSUFFICIENT_INFORMATION.value: set(),
    DecisionState.OUTSIDE_PROTOTYPE_COVERAGE.value: set(),
    DecisionState.CONTRADICTORY_SPECIFICATIONS.value: set(),
    DecisionState.EXPERT_REVIEW_REQUIRED.value: set(),
}


def get_state_spec(state: str) -> Optional[DecisionStateSpec]:
    """Get the specification for a decision state."""
    return DECISION_STATE_SPECS.get(state)


def get_claim_level(state: str) -> str:
    """Get the claim level for a decision state."""
    spec = DECISION_STATE_SPECS.get(state)
    if spec:
        return spec.claim_level.value
    return ClaimLevel.ABSTAINED.value


def is_valid_transition(from_state: str, to_state: str) -> bool:
    """Check if a state transition is valid."""
    valid = VALID_TRANSITIONS.get(from_state, set())
    return to_state in valid


def validate_decision_output(output: Dict[str, Any]) -> List[str]:
    """
    Validate a recommendation engine output for decision state invariants.
    Returns list of violations (empty = valid).
    """
    violations = []
    state = output.get("decision_state")

    # 1. State must be a recognized DecisionState
    try:
        DecisionState(state)
    except (ValueError, KeyError):
        violations.append(f"Unknown decision state: {state}")
        return violations

    spec = DECISION_STATE_SPECS.get(state)
    if not spec:
        violations.append(f"No specification for state: {state}")
        return violations

    # 2. If state requires primary, output must have one
    if spec.requires_primary and not output.get("primary_recommendation"):
        violations.append(f"State {state} requires primary_recommendation but none present")

    # 3. If state is abstention, primary must be None
    if spec.is_abstention and output.get("primary_recommendation"):
        violations.append(f"Abstention state {state} must not have primary_recommendation")

    # 4. If state requires review candidate, must be present
    if spec.requires_review_candidate and not output.get("review_candidate"):
        # This is a warning, not a hard violation
        pass

    # 5. Claim level consistency
    claim = output.get("claim_level")
    if claim and claim != spec.claim_level.value:
        # Allow downgrade but not upgrade
        claim_order = [
            ClaimLevel.ABSTAINED.value,
            ClaimLevel.REVIEW_REQUIRED.value,
            ClaimLevel.PLAUSIBLE.value,
            ClaimLevel.VERIFIED_FOR_RECOMMENDATION.value,
        ]
        if claim in claim_order and spec.claim_level.value in claim_order:
            claim_idx = claim_order.index(claim)
            spec_idx = claim_order.index(spec.claim_level.value)
            if claim_idx > spec_idx:
                violations.append(
                    f"Claim level {claim} is stronger than state {state} allows ({spec.claim_level.value})"
                )

    return violations
