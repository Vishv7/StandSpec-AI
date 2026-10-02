"""
StandSpec AI — Deterministic Response Validator & Safety Gate (Phase P1-F Section 15-17)
The deterministic validator is the authoritative safety barrier.
It evaluates any LLM proposed answer against ground truth tool evidence:
  1. Candidate presence: Designation must exist in tool retrieval candidates or be explicitly requested.
  2. Role validity: Cannot promote supporting standards (test methods, mountings, codes) as primary product standard.
  3. Applicability grounding: Cannot recommend candidate evaluated as NOT_APPLICABLE or MISMATCH.
  4. Explicit designation conflict: If requested standard mismatches product (e.g. uPVC pipe + IS 1180), primary must be null.
  5. Regulatory truthfulness: Cannot claim 'not mandatory' when state is unverified; cannot invent QCO orders.
  6. Lifecycle validity: Cannot recommend obsolete or invalid editions when active editions exist.
"""

from typing import Dict, Any, List, Optional, Tuple
import re
import logging

logger = logging.getLogger("DeterministicValidator")


class ValidationResult:
    """Outcome of safety validation."""
    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None, veto_reasons: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.veto_reasons = veto_reasons or []

    def __bool__(self):
        return self.is_valid


class DeterministicValidator:
    """
    Hard-gate safety validator for agent proposals.
    Vetoes ungrounded, hallucinated, or policy-violating proposals.
    """

    def __init__(self, standards_graph: Optional[dict] = None):
        self.standards_graph = standards_graph or {}
        self.nodes_by_desig = {}
        for n in self.standards_graph.get("nodes", []):
            d = n.get("designation", "").strip()
            if d:
                self.nodes_by_desig[d] = n
                base = d.split(":")[0].strip()
                if base not in self.nodes_by_desig:
                    self.nodes_by_desig[base] = n

    def _resolve_base(self, desig: str) -> str:
        if not desig:
            return ""
        d = desig.split(":")[0].strip().lower()
        d = re.sub(r"[\(\)]", "", d)
        d = re.sub(r"\s+", " ", d).strip()
        return d

    def _find_candidate_dict(self, target_desig: str, mapping: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not target_desig or not mapping:
            return None
        if target_desig in mapping:
            return mapping[target_desig]
        base = self._resolve_base(target_desig)
        if base in mapping:
            return mapping[base]
        for k, v in mapping.items():
            if self._resolve_base(k) == base:
                return v
        return None

    def validate(
        self,
        proposal: Dict[str, Any],
        raw_query: str,
        retrieved_candidates: List[Dict[str, Any]],
        candidate_applicability: Dict[str, Any],
        candidate_lifecycle: Dict[str, Any],
        candidate_regulatory: Dict[str, Any],
        requested_designations: Optional[List[str]] = None,
    ) -> ValidationResult:
        """
        Validates the proposed final answer against hard safety gates.
        Returns ValidationResult(is_valid=True) or ValidationResult(is_valid=False, errors=[...]).
        """
        errors = []
        veto_reasons = []

        if not isinstance(proposal, dict):
            return ValidationResult(False, ["Proposal is not a dictionary."])

        decision_state = proposal.get("decision_state")
        valid_states = (
            "PRIMARY_RECOMMENDATION_AVAILABLE",
            "CONDITIONAL_RECOMMENDATION",
            "MULTIPLE_POSSIBLE_STANDARDS",
            "INSUFFICIENT_INFORMATION",
            "NO_CONFIDENT_MATCH",
            "STANDARD_DATA_UNAVAILABLE",
            "OUTSIDE_PROTOTYPE_COVERAGE",
            "EXPERT_REVIEW_REQUIRED",
            "CLARIFICATION_REQUIRED",
            "CONTRADICTORY_SPECIFICATIONS",
        )
        if not decision_state or decision_state not in valid_states:
            errors.append(f"Invalid or missing decision_state: '{decision_state}'. Must be one of {valid_states}.")
            veto_reasons.append("INVALID_DECISION_STATE")
            return ValidationResult(False, errors=errors, veto_reasons=veto_reasons)

        primary = proposal.get("primary_recommendation")
        requested_desigs = [self._resolve_base(d) for d in (requested_designations or [])]

        # Allowed designations: candidates returned by tools + explicitly requested
        allowed_bases = {
            self._resolve_base(c.get("designation", ""))
            for c in retrieved_candidates
            if isinstance(c, dict)
        }
        for d in requested_desigs:
            if d:
                allowed_bases.add(d)

        # ── GATE 1: Null-Primary Safety on Abstention States ──
        abstention_states = (
            "NO_CONFIDENT_MATCH",
            "INSUFFICIENT_INFORMATION",
            "OUTSIDE_PROTOTYPE_COVERAGE",
            "EXPERT_REVIEW_REQUIRED",
            "CLARIFICATION_REQUIRED",
            "STANDARD_DATA_UNAVAILABLE",
            "CONTRADICTORY_SPECIFICATIONS",
        )
        if decision_state in abstention_states and primary is not None:
            errors.append(f"State '{decision_state}' must have primary_recommendation=null, but primary was proposed.")
            veto_reasons.append("NULL_PRIMARY_VIOLATION")

        # If primary recommendation is proposed, apply strict verification gates:
        if primary and isinstance(primary, dict):
            desig = primary.get("designation", "").strip()
            base_desig = self._resolve_base(desig)

            # ── GATE 2: Candidate Presence (Anti-Hallucination) ──
            if not base_desig or base_desig not in allowed_bases:
                errors.append(
                    f"Hallucinated candidate: '{desig}' was neither returned by search_standards nor explicitly requested."
                )
                veto_reasons.append("HALLUCINATED_DESIGNATION")

            # ── GATE 2B: Prototype Department Boundary Gate (CED + ETD Only) ──
            node = self.nodes_by_desig.get(desig) or self.nodes_by_desig.get(base_desig)
            if node:
                from src.recommendation.corpus_policy import PrototypeCoveragePolicy
                if not PrototypeCoveragePolicy.is_in_primary_coverage(node):
                    errors.append(
                        f"Department Boundary Veto: '{desig}' is outside supported prototype departments (CED/ETD only)."
                    )
                    veto_reasons.append("OUTSIDE_PROTOTYPE_COVERAGE")

            # ── GATE 3: Role Validity (No Supporting Standards as Primary Products) ──
            cand_meta = next((c for c in retrieved_candidates if self._resolve_base(c.get("designation", "")) == base_desig), None)
            if cand_meta:
                role = cand_meta.get("role", "PRIMARY_PRODUCT")
                query_lower = raw_query.lower()
                is_explicit_test_intent = any(w in query_lower for w in ("test method", "testing code", "method of test", "sampling"))
                is_explicit_code_intent = any(w in query_lower for w in ("code of practice", "design code", "installation code"))

                if role in ("TEST_METHOD", "SUPPORTING_OTHER", "COMPONENT", "MOUNTING_OR_DIMENSION"):
                    if role == "TEST_METHOD" and not is_explicit_test_intent:
                        errors.append(f"Wrong Role: '{desig}' is a {role} and cannot be primary product recommendation.")
                        veto_reasons.append("WRONG_ROLE_PRIMARY")
                    elif role in ("SUPPORTING_OTHER", "MOUNTING_OR_DIMENSION") and not is_explicit_code_intent:
                        errors.append(f"Wrong Role: '{desig}' is a supporting/mounting standard ({role}) not a primary product.")
                        veto_reasons.append("WRONG_ROLE_PRIMARY")

            # ── GATE 4: Technical Applicability Gate (No Mismatches) ──
            app = self._find_candidate_dict(desig, candidate_applicability)
            if app:
                app_state = app.get("applicability_state", "UNKNOWN")
                mismatches = app.get("mismatched_attributes", [])
                exclusions = app.get("exclusions_triggered", [])

                if app_state in ("NOT_APPLICABLE", "INCOMPATIBLE"):
                    errors.append(f"Inapplicable Candidate: '{desig}' evaluated as NOT_APPLICABLE.")
                    veto_reasons.append("APPLICABILITY_MISMATCH")
                elif mismatches:
                    errors.append(f"Attribute Mismatches: '{desig}' has conflicting attributes: {mismatches}")
                    veto_reasons.append("ATTRIBUTE_MISMATCH")
                elif exclusions:
                    errors.append(f"Exclusion Boundary: '{desig}' triggered exclusion boundaries: {exclusions}")
                    veto_reasons.append("EXCLUSION_BOUNDARY_TRIGGERED")

            # ── GATE 5: Explicit Designation Conflict Check (IS 1180 vs uPVC pipe) ──
            if requested_desigs and base_desig in requested_desigs:
                # If requested designation had an applicability evaluation and failed to positively match, must NOT recommend!
                if app and (app.get("applicability_state") != "APPLICABLE" or app.get("mismatched_attributes")):
                    errors.append(
                        f"Explicit Requested Standard Mismatch: '{desig}' was requested but does not match query requirements."
                    )
                    veto_reasons.append("REQUESTED_STANDARD_MISMATCH")

            # ── GATE 6: Lifecycle Gate (No Obsolete Predecessors) ──
            life = self._find_candidate_dict(desig, candidate_lifecycle)
            if life:
                life_state = life.get("lifecycle_state", "ACTIVE_VALID")
                if life_state in ("WITHDRAWN", "OBSOLETE_PREDECESSOR"):
                    errors.append(f"Lifecycle Veto: '{desig}' is {life_state} and cannot be recommended as active.")
                    veto_reasons.append("LIFECYCLE_VETO")

        # ── GATE 7: Regulatory Fidelity Gate ──
        regulatory = proposal.get("regulatory", {})
        if isinstance(regulatory, dict):
            reg_state = regulatory.get("state", "NOT_VERIFIED_IN_CURRENT_CORPUS")
            statement = (regulatory.get("statement") or "").lower()
            explanation = (proposal.get("natural_language_explanation") or "").lower()

            if reg_state in ("NOT_VERIFIED_IN_CURRENT_CORPUS", "UNVERIFIED"):
                if regulatory.get("qco_order_number"):
                    errors.append(
                        "Regulatory Violation: Cannot cite specific QCO order number when regulatory status is unverified in corpus."
                    )
                    veto_reasons.append("HALLUCINATED_QCO")
                if "not mandatory" in statement or "voluntary" in statement:
                    errors.append(
                        "Regulatory Violation: Cannot claim standard is 'not mandatory' or 'voluntary' when status is unverified."
                    )
                    veto_reasons.append("REGULATORY_FALSE_ASSERTION")
                if "not mandatory" in explanation or "is voluntary" in explanation:
                    errors.append(
                        "Regulatory Explanation Violation: Cannot assert 'not mandatory' or 'voluntary' in explanation for unverified status."
                    )
                    veto_reasons.append("REGULATORY_FALSE_ASSERTION")
            elif reg_state == "MANDATORY_CONFIRMED":
                if "not mandatory" in statement or "voluntary" in statement:
                    errors.append("Regulatory Violation: Cannot claim mandatory standard is voluntary.")
                    veto_reasons.append("REGULATORY_FALSE_ASSERTION")

        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors, veto_reasons=veto_reasons)
