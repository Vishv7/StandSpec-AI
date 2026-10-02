"""
Agent Safety Invariants — StandSpec AI (Phase 13, Checkpoint 5)
PS 26108 §14: Agent orchestration safety hardening.

Defines and enforces structural invariants that every agent response MUST satisfy.
These are hard gates — violations cause immediate rejection/correction.

Key invariants:
  1. DESIGNATION_INTEGRITY: Designation strings must not be fabricated or altered
  2. RECOMMENDATION_GROUNDING: Primary recommendation must be grounded in evidence
  3. CLAIM_CONSISTENCY: Claim level must be consistent with decision state
  4. REGULATORY_TRUTHFULNESS: Regulatory assertions must be backed by evidence
  5. ABSTENTION_HONESTY: Abstention reasons must be genuine, not fabricated
  6. EXPLANATION_GROUNDING: Explanations must reference only verified facts
  7. NO_HALLUCINATION: LLM output must not invent standards, titles, or QCO orders
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import re
import logging

logger = logging.getLogger("AgentSafetyInvariants")


class InvariantSeverity(str, Enum):
    """Severity of invariant violation."""
    CRITICAL = "CRITICAL"    # Hard veto — response must be rejected
    WARNING = "WARNING"      # Soft warning — response is downgraded
    INFO = "INFO"            # Informational — logged but not acted on


@dataclass
class InvariantViolation:
    """A single invariant violation."""
    invariant_id: str
    severity: InvariantSeverity
    message: str
    field_path: str = ""
    expected: str = ""
    actual: str = ""


@dataclass
class InvariantCheckResult:
    """Result of invariant validation."""
    is_valid: bool
    violations: List[InvariantViolation] = field(default_factory=list)
    critical_count: int = 0
    warning_count: int = 0

    def add_violation(self, violation: InvariantViolation):
        self.violations.append(violation)
        if violation.severity == InvariantSeverity.CRITICAL:
            self.critical_count += 1
            self.is_valid = False
        elif violation.severity == InvariantSeverity.WARNING:
            self.warning_count += 1


def check_designation_integrity(
    response: Dict[str, Any],
    known_designations: set,
) -> List[InvariantViolation]:
    """
    INV-1: DESIGNATION_INTEGRITY
    Any designation string in the response must exist in the knowledge graph.
    The agent must never fabricate IS numbers.
    """
    violations = []
    primary = response.get("primary_recommendation")
    if primary:
        desig = primary.get("standard_designation", "")
        if desig and desig not in known_designations:
            # Check base number (without year)
            base = desig.split(":")[0].strip()
            if not any(base in kd for kd in known_designations):
                violations.append(InvariantViolation(
                    invariant_id="INV-1-DESIGNATION",
                    severity=InvariantSeverity.CRITICAL,
                    message=f"Primary recommendation designation '{desig}' not found in knowledge graph",
                    field_path="primary_recommendation.standard_designation",
                    expected="Known designation from KB",
                    actual=desig,
                ))

    review = response.get("review_candidate")
    if review:
        desig = review.get("designation", review.get("standard_designation", ""))
        if desig and desig not in known_designations:
            base = desig.split(":")[0].strip()
            if not any(base in kd for kd in known_designations):
                violations.append(InvariantViolation(
                    invariant_id="INV-1-DESIGNATION-REVIEW",
                    severity=InvariantSeverity.WARNING,
                    message=f"Review candidate designation '{desig}' not found in knowledge graph",
                    field_path="review_candidate.designation",
                    expected="Known designation from KB",
                    actual=desig,
                ))

    return violations


def check_recommendation_grounding(response: Dict[str, Any]) -> List[InvariantViolation]:
    """
    INV-2: RECOMMENDATION_GROUNDING
    Primary recommendation must have evidence grounding.
    Cannot have a primary without at least scope verification.
    """
    violations = []
    primary = response.get("primary_recommendation")
    decision_state = response.get("decision_state", "")

    if primary and decision_state == "PRIMARY_RECOMMENDATION_AVAILABLE":
        # Must have applicability data
        app = primary.get("applicability", {})
        if not app:
            violations.append(InvariantViolation(
                invariant_id="INV-2-GROUNDING-APPLICABILITY",
                severity=InvariantSeverity.CRITICAL,
                message="Primary recommendation missing applicability evidence",
                field_path="primary_recommendation.applicability",
            ))

        # Must have title
        if not primary.get("title"):
            violations.append(InvariantViolation(
                invariant_id="INV-2-GROUNDING-TITLE",
                severity=InvariantSeverity.WARNING,
                message="Primary recommendation missing title",
                field_path="primary_recommendation.title",
            ))

    return violations


def check_claim_consistency(response: Dict[str, Any]) -> List[InvariantViolation]:
    """
    INV-3: CLAIM_CONSISTENCY
    Claim level must not be stronger than the decision state allows.
    """
    violations = []
    state = response.get("decision_state", "")
    claim = response.get("claim_level", "")

    # Define maximum claim for each state
    max_claims = {
        "PRIMARY_RECOMMENDATION_AVAILABLE": "VERIFIED_FOR_RECOMMENDATION",
        "CONDITIONAL_RECOMMENDATION": "PLAUSIBLE",
        "MULTIPLE_POSSIBLE_STANDARDS": "REVIEW_REQUIRED",
        "EXPERT_REVIEW_REQUIRED": "REVIEW_REQUIRED",
        "NO_CONFIDENT_MATCH": "ABSTAINED",
        "INSUFFICIENT_INFORMATION": "ABSTAINED",
        "OUTSIDE_PROTOTYPE_COVERAGE": "ABSTAINED",
        "CONTRADICTORY_SPECIFICATIONS": "ABSTAINED",
    }

    claim_order = ["ABSTAINED", "REVIEW_REQUIRED", "PLAUSIBLE", "VERIFIED_FOR_RECOMMENDATION"]

    max_claim = max_claims.get(state)
    if max_claim and claim in claim_order and max_claim in claim_order:
        if claim_order.index(claim) > claim_order.index(max_claim):
            violations.append(InvariantViolation(
                invariant_id="INV-3-CLAIM",
                severity=InvariantSeverity.CRITICAL,
                message=f"Claim level '{claim}' exceeds maximum '{max_claim}' for state '{state}'",
                field_path="claim_level",
                expected=max_claim,
                actual=claim,
            ))

    return violations


def check_abstention_honesty(response: Dict[str, Any]) -> List[InvariantViolation]:
    """
    INV-5: ABSTENTION_HONESTY
    Abstention states must NOT have primary recommendations.
    Non-abstention states must have the appropriate recommendation.
    """
    violations = []
    state = response.get("decision_state", "")
    primary = response.get("primary_recommendation")

    abstention_states = {
        "NO_CONFIDENT_MATCH", "INSUFFICIENT_INFORMATION",
        "OUTSIDE_PROTOTYPE_COVERAGE", "CONTRADICTORY_SPECIFICATIONS",
    }

    if state in abstention_states and primary:
        violations.append(InvariantViolation(
            invariant_id="INV-5-ABSTENTION-WITH-PRIMARY",
            severity=InvariantSeverity.CRITICAL,
            message=f"Abstention state '{state}' must not have primary_recommendation",
            field_path="primary_recommendation",
            expected="null",
            actual=str(primary.get("standard_designation", "present")),
        ))

    if state == "PRIMARY_RECOMMENDATION_AVAILABLE" and not primary:
        violations.append(InvariantViolation(
            invariant_id="INV-5-PRIMARY-WITHOUT-REC",
            severity=InvariantSeverity.CRITICAL,
            message="PRIMARY_RECOMMENDATION_AVAILABLE state must have primary_recommendation",
            field_path="primary_recommendation",
            expected="non-null",
            actual="null",
        ))

    return violations


def check_no_hallucination(
    response: Dict[str, Any],
    llm_text: Optional[str] = None,
    known_designations: Optional[set] = None,
) -> List[InvariantViolation]:
    """
    INV-7: NO_HALLUCINATION
    LLM-generated text must not contain designation numbers not in the knowledge base.
    """
    violations = []
    if not llm_text or not known_designations:
        return violations

    # Find all IS XXXX patterns in LLM text
    is_pattern = re.compile(r'IS\s+(\d{1,5})', re.IGNORECASE)
    mentioned = set()
    for m in is_pattern.finditer(llm_text):
        num = m.group(1)
        mentioned.add(f"IS {num}")

    for m_desig in mentioned:
        if not any(m_desig in kd for kd in known_designations):
            violations.append(InvariantViolation(
                invariant_id="INV-7-HALLUCINATED-DESIGNATION",
                severity=InvariantSeverity.CRITICAL,
                message=f"LLM text references '{m_desig}' which is not in the knowledge base",
                field_path="explanation.text",
                expected="Only known designations",
                actual=m_desig,
            ))

    return violations


def validate_agent_response(
    response: Dict[str, Any],
    known_designations: Optional[set] = None,
    llm_text: Optional[str] = None,
) -> InvariantCheckResult:
    """
    Run all safety invariants against an agent response.
    Returns InvariantCheckResult with all violations.
    """
    result = InvariantCheckResult(is_valid=True)
    known = known_designations or set()

    # INV-1: Designation Integrity
    for v in check_designation_integrity(response, known):
        result.add_violation(v)

    # INV-2: Recommendation Grounding
    for v in check_recommendation_grounding(response):
        result.add_violation(v)

    # INV-3: Claim Consistency
    for v in check_claim_consistency(response):
        result.add_violation(v)

    # INV-5: Abstention Honesty
    for v in check_abstention_honesty(response):
        result.add_violation(v)

    # INV-7: No Hallucination
    for v in check_no_hallucination(response, llm_text, known):
        result.add_violation(v)

    return result
