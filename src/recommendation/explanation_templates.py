"""
Structured Explanation Templates — StandSpec AI (Phase 11, Checkpoint 4)
PS 26108 §12: Deterministic, template-based explanation generation per decision state.

Generates human-readable, structured explanations for every decision state
WITHOUT relying on LLM generation. These templates serve as:
  1. The fallback explanation when LLM is unavailable or fails validation
  2. The structured basis for LLM explanation grounding
  3. The canonical format for audit-trail explanation records

Key principle: LLM UNDERSTANDS. Deterministic system DECIDES. LLM EXPLAINS.
Templates ensure the deterministic layer always has a coherent explanation.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class StructuredExplanation:
    """
    A structured explanation that can be rendered to different formats.
    Contains all evidence-grounded facts and no hallucinated content.
    """
    decision_state: str
    headline: str
    summary: str
    evidence_points: List[str] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)
    user_action: str = ""
    standard_designation: Optional[str] = None
    standard_title: Optional[str] = None
    confidence_pct: Optional[float] = None
    claim_level: str = "ABSTAINED"

    def to_text(self) -> str:
        """Render explanation as plain text."""
        lines = [self.headline, "", self.summary]
        if self.evidence_points:
            lines.append("")
            lines.append("Evidence:")
            for i, ep in enumerate(self.evidence_points, 1):
                lines.append(f"  {i}. {ep}")
        if self.caveats:
            lines.append("")
            lines.append("Caveats:")
            for c in self.caveats:
                lines.append(f"  ⚠ {c}")
        if self.user_action:
            lines.append("")
            lines.append(f"Recommended Action: {self.user_action}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Render explanation as structured dict for API responses."""
        return {
            "decision_state": self.decision_state,
            "headline": self.headline,
            "summary": self.summary,
            "evidence_points": self.evidence_points,
            "caveats": self.caveats,
            "user_action": self.user_action,
            "standard_designation": self.standard_designation,
            "standard_title": self.standard_title,
            "confidence_pct": self.confidence_pct,
            "claim_level": self.claim_level,
        }


def generate_explanation(rec_result: Dict[str, Any]) -> StructuredExplanation:
    """
    Generate a structured explanation from a recommendation engine result.
    Deterministic, template-based — no LLM required.
    """
    decision_state = rec_result.get("decision_state", "UNKNOWN")
    primary = rec_result.get("primary_recommendation")
    review = rec_result.get("review_candidate")
    abstention_reason = rec_result.get("abstention_reason", "")

    # Route to the appropriate template
    if decision_state == "PRIMARY_RECOMMENDATION_AVAILABLE":
        return _explain_primary(rec_result, primary)
    elif decision_state == "CONDITIONAL_RECOMMENDATION":
        return _explain_conditional(rec_result, primary)
    elif decision_state == "MULTIPLE_POSSIBLE_STANDARDS":
        return _explain_multiple(rec_result, primary)
    elif decision_state == "EXPERT_REVIEW_REQUIRED":
        return _explain_review(rec_result, review)
    elif decision_state == "NO_CONFIDENT_MATCH":
        return _explain_no_match(rec_result)
    elif decision_state == "INSUFFICIENT_INFORMATION":
        return _explain_insufficient(rec_result)
    elif decision_state == "OUTSIDE_PROTOTYPE_COVERAGE":
        return _explain_out_of_scope(rec_result)
    elif decision_state == "CONTRADICTORY_SPECIFICATIONS":
        return _explain_contradictory(rec_result)
    else:
        return _explain_unknown(rec_result)


def _explain_primary(result: Dict, primary: Dict) -> StructuredExplanation:
    """Template for PRIMARY_RECOMMENDATION_AVAILABLE."""
    desig = primary.get("standard_designation", "Unknown")
    title = primary.get("title", "")
    conf = primary.get("calibrated_confidence", 0.0)
    app = primary.get("applicability", {})
    matched = app.get("matched_attributes", [])
    reg = primary.get("regulatory", {})
    reg_state = reg.get("regulatory_state", "NOT_VERIFIED")
    lifecycle = primary.get("lifecycle", {})

    evidence = []
    if matched:
        evidence.append(f"Technical attributes verified: {', '.join(matched)}")
    if reg_state == "MANDATORY_VIA_QCO":
        qco = reg.get("qco_order_number") or reg.get("gazette_so_number", "")
        evidence.append(f"Regulatory mandate: Quality Control Order ({qco})")
    elif reg_state == "VOLUNTARY":
        evidence.append("Regulatory status: Voluntary standard (no QCO mandate)")
    if lifecycle.get("recommended_edition"):
        evidence.append(f"Recommended edition: {lifecycle['recommended_edition']}")

    caveats = []
    if conf < 0.70:
        caveats.append(f"Confidence ({conf:.0%}) is below 70% — verify against specific tender requirements")
    if lifecycle.get("amendment_notes"):
        caveats.append(f"Amendment note: {lifecycle['amendment_notes']}")

    return StructuredExplanation(
        decision_state="PRIMARY_RECOMMENDATION_AVAILABLE",
        headline=f"Recommended Standard: {desig}",
        summary=f"{desig} ({title}) is recommended for this procurement query.",
        evidence_points=evidence,
        caveats=caveats,
        user_action="Review the matched attributes and verify against your specific tender requirements.",
        standard_designation=desig,
        standard_title=title,
        confidence_pct=round(conf * 100, 1),
        claim_level="VERIFIED_FOR_RECOMMENDATION",
    )


def _explain_conditional(result: Dict, primary: Dict) -> StructuredExplanation:
    """Template for CONDITIONAL_RECOMMENDATION."""
    desig = primary.get("standard_designation", "Unknown")
    title = primary.get("title", "")
    conf = primary.get("calibrated_confidence", 0.0)
    conditions = result.get("abstention_reason", "")

    return StructuredExplanation(
        decision_state="CONDITIONAL_RECOMMENDATION",
        headline=f"Conditional Recommendation: {desig}",
        summary=f"{desig} ({title}) is recommended with conditions.",
        evidence_points=[
            f"Calibrated confidence: {conf:.0%}",
            f"Conditions: {conditions}" if conditions else "Some technical parameters are unverified",
        ],
        caveats=["This recommendation is conditional — not all parameters have been fully verified"],
        user_action="Verify the unconfirmed conditions before making final procurement decisions.",
        standard_designation=desig,
        standard_title=title,
        confidence_pct=round(conf * 100, 1),
        claim_level="PLAUSIBLE",
    )


def _explain_multiple(result: Dict, primary: Optional[Dict]) -> StructuredExplanation:
    """Template for MULTIPLE_POSSIBLE_STANDARDS."""
    viable = result.get("candidate_recommendations", [])
    n_viable = len(viable)

    evidence = [f"{n_viable} candidate standards match the query with similar confidence"]
    if primary:
        desig = primary.get("standard_designation", "Unknown")
        evidence.append(f"Top candidate: {desig}")

    return StructuredExplanation(
        decision_state="MULTIPLE_POSSIBLE_STANDARDS",
        headline=f"Multiple Standards Match ({n_viable} candidates)",
        summary="Multiple standards match the procurement query. Additional specifications are needed to disambiguate.",
        evidence_points=evidence,
        caveats=["Cannot determine a single best match — additional discriminating specifications required"],
        user_action="Provide additional technical specifications (material, voltage class, grade, application type) to narrow the match.",
        claim_level="REVIEW_REQUIRED",
    )


def _explain_review(result: Dict, review: Optional[Dict]) -> StructuredExplanation:
    """Template for EXPERT_REVIEW_REQUIRED."""
    evidence = []
    caveats = []

    if review:
        desig = review.get("designation", review.get("standard_designation", "Unknown"))
        title = review.get("title", "")
        evidence.append(f"Review candidate: {desig} ({title})")

        missing = review.get("missing_evidence", review.get("evidence_gaps", []))
        if missing:
            evidence.append(f"Missing evidence: {', '.join(str(m) for m in missing)}")
            caveats.append("Candidate lacks verified evidence for automated recommendation")
    else:
        desig = None

    return StructuredExplanation(
        decision_state="EXPERT_REVIEW_REQUIRED",
        headline=f"Expert Review Required{f': {desig}' if desig else ''}",
        summary="A plausible candidate was identified but requires expert verification.",
        evidence_points=evidence,
        caveats=caveats or ["Insufficient verified evidence for automated recommendation"],
        user_action="Consult with a domain expert to verify the identified candidate against tender requirements.",
        standard_designation=desig,
        claim_level="REVIEW_REQUIRED",
    )


def _explain_no_match(result: Dict) -> StructuredExplanation:
    """Template for NO_CONFIDENT_MATCH."""
    reason = result.get("abstention_reason", "")

    return StructuredExplanation(
        decision_state="NO_CONFIDENT_MATCH",
        headline="No Confident Match Found",
        summary="No candidate standard achieved sufficient confidence for recommendation.",
        evidence_points=[f"Reason: {reason}"] if reason else [],
        caveats=["The system abstained rather than risk an incorrect recommendation"],
        user_action="Refine the procurement query with more specific technical parameters or consult domain experts.",
        claim_level="ABSTAINED",
    )


def _explain_insufficient(result: Dict) -> StructuredExplanation:
    """Template for INSUFFICIENT_INFORMATION."""
    reason = result.get("abstention_reason", "")
    req_obj = result.get("normalized_requirements", {})
    missing = req_obj.get("missing_discriminators", [])

    evidence = []
    if missing:
        evidence.append(f"Missing discriminators: {', '.join(missing)}")
    if reason:
        evidence.append(f"Detail: {reason}")

    return StructuredExplanation(
        decision_state="INSUFFICIENT_INFORMATION",
        headline="Insufficient Information",
        summary="The procurement query lacks critical discriminating information for an unambiguous recommendation.",
        evidence_points=evidence,
        caveats=["Additional specifications are required before the system can provide a reliable recommendation"],
        user_action=f"Provide: {', '.join(missing)}" if missing else "Provide more specific technical details.",
        claim_level="ABSTAINED",
    )


def _explain_out_of_scope(result: Dict) -> StructuredExplanation:
    """Template for OUTSIDE_PROTOTYPE_COVERAGE."""
    return StructuredExplanation(
        decision_state="OUTSIDE_PROTOTYPE_COVERAGE",
        headline="Outside System Scope",
        summary="The procurement query specifies products outside the current system coverage (CED + ETD divisions).",
        evidence_points=["The system currently covers Civil Engineering Division (CED) and Electrotechnical Division (ETD) standards only"],
        caveats=["This is NOT a standard recommendation — the system cannot evaluate products outside its coverage boundary"],
        user_action="Consult BIS directly for standards in other divisions.",
        claim_level="ABSTAINED",
    )


def _explain_contradictory(result: Dict) -> StructuredExplanation:
    """Template for CONTRADICTORY_SPECIFICATIONS."""
    reason = result.get("abstention_reason", "")
    req_obj = result.get("normalized_requirements", {})
    contradictions = req_obj.get("contradictions", [])

    evidence = []
    if contradictions:
        for c in contradictions[:5]:
            evidence.append(f"Contradiction: {c}")
    elif reason:
        evidence.append(f"Detail: {reason}")

    return StructuredExplanation(
        decision_state="CONTRADICTORY_SPECIFICATIONS",
        headline="Contradictory Specifications Detected",
        summary="The procurement query contains contradictory technical specifications that cannot be simultaneously satisfied.",
        evidence_points=evidence,
        caveats=["No recommendation is possible until the contradictions are resolved"],
        user_action="Review and resolve the contradictory technical requirements in the tender specification.",
        claim_level="ABSTAINED",
    )


def _explain_unknown(result: Dict) -> StructuredExplanation:
    """Fallback template for unknown states."""
    state = result.get("decision_state", "UNKNOWN")
    return StructuredExplanation(
        decision_state=state,
        headline=f"Decision State: {state}",
        summary=f"The system reached decision state '{state}'.",
        user_action="Review the full system output for details.",
        claim_level="ABSTAINED",
    )
