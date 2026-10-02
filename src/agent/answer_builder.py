"""
StandSpec AI — Answer Builder (Phase P1-F Section 14, 24, 25)
Constructs compliant, dual-format (machine JSON + human natural language) responses
adhering strictly to schemas/agent_final_answer.schema.json.
"""

from typing import Dict, Any, List, Optional
import json


class AnswerBuilder:
    """Builds and serializes agent final answers."""

    @staticmethod
    def build_deterministic_answer(
        decision_state: str,
        primary_candidate: Optional[Dict[str, Any]] = None,
        alternatives: Optional[List[Dict[str, Any]]] = None,
        review_candidate: Optional[Dict[str, Any]] = None,
        clarifications_needed: Optional[List[str]] = None,
        clarification_category: Optional[str] = None,
        normalized_requirements: Optional[Dict[str, Any]] = None,
        lifecycle_meta: Optional[Dict[str, Any]] = None,
        regulatory_meta: Optional[Dict[str, Any]] = None,
        provenance: Optional[List[str]] = None,
        confidence: str = "UNVERIFIED",
        explanation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Constructs a deterministic, evidence-grounded final answer."""
        primary_rec = None
        if primary_candidate and decision_state in ("PRIMARY_RECOMMENDATION_AVAILABLE", "CONDITIONAL_RECOMMENDATION"):
            desig = primary_candidate.get("designation")
            title = primary_candidate.get("title")
            matched = primary_candidate.get("matched_attributes", [])
            primary_rec = {
                "designation": desig,
                "title": title,
                "reason": primary_candidate.get("reason", f"Matched procurement specifications for {matched}."),
                "applicability_state": primary_candidate.get("applicability_state", "APPLICABLE"),
                "claim_level": primary_candidate.get("claim_level", "VERIFIED"),
                "evidence_ids": primary_candidate.get("evidence_ids", []),
                "matched_attributes": matched,
            }

        alts = []
        for alt in (alternatives or []):
            if isinstance(alt, dict) and alt.get("designation"):
                alts.append({
                    "designation": alt.get("designation"),
                    "title": alt.get("title", ""),
                    "reason": alt.get("reason", "Alternative candidate standard"),
                    "evidence_ids": alt.get("evidence_ids", []),
                })

        rev = None
        if review_candidate:
            rev = {
                "designation": review_candidate.get("designation", "Unknown"),
                "title": review_candidate.get("title", ""),
                "reason": review_candidate.get("reason", "Requires expert engineering review"),
                "evidence_gaps": review_candidate.get("evidence_gaps", []),
                "evidence_ids": review_candidate.get("evidence_ids", []),
            }

        # Lifecycle block
        life = {
            "state": (lifecycle_meta or {}).get("lifecycle_state", "LIFECYCLE_UNKNOWN"),
            "recommended_edition": (lifecycle_meta or {}).get("recommended_edition"),
            "superseded_by": (lifecycle_meta or {}).get("superseded_by"),
            "evidence": (lifecycle_meta or {}).get("evidence", []),
        }

        # Regulatory block
        reg_state = (regulatory_meta or {}).get("regulatory_state", "NOT_VERIFIED_IN_CURRENT_CORPUS")
        reg_statement = (regulatory_meta or {}).get("statement")
        if not reg_statement:
            if reg_state == "MANDATORY_CONFIRMED":
                qco = (regulatory_meta or {}).get("qco_order_number") or "QCO"
                reg_statement = f"Indexed regulatory evidence indicates mandatory certification under Gazette Order {qco}."
            elif reg_state == "MANDATORY_CONDITIONALLY_APPLICABLE":
                qco = (regulatory_meta or {}).get("qco_order_number") or "conditional mandate"
                reg_statement = f"Indexed regulatory evidence indicates mandatory certification subject to conditions ({qco})."
            elif reg_state in ("NOT_VERIFIED_IN_CURRENT_CORPUS", "UNVERIFIED", "UNKNOWN", "MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES"):
                reg_statement = "Regulatory status is not verified in the indexed corpus. No applicable regulatory record or order was found."
            elif reg_state == "CONFLICTING_EVIDENCE":
                reg_statement = "Conflicting regulatory evidence prevents a verified mandate conclusion."
            elif reg_state == "VOLUNTARY_OR_UNLISTED":
                reg_statement = "Regulatory status is not verified in current corpus. No applicable regulatory mandate was found."
            elif reg_state == "REGULATORY_SOURCE_UNAVAILABLE":
                reg_statement = "Regulatory source unavailable in current corpus."
            else:
                reg_statement = f"Regulatory evidence status: {reg_state}."

        reg = {
            "state": reg_state,
            "qco_order_number": (regulatory_meta or {}).get("qco_order_number"),
            "gazette_so_number": (regulatory_meta or {}).get("gazette_so_number"),
            "effective_date": (regulatory_meta or {}).get("effective_date"),
            "statement": reg_statement,
            "evidence": (regulatory_meta or {}).get("evidence", []),
        }

        # Human-readable explanation
        if not explanation:
            parts = [f"Decision State: {decision_state}."]
            if primary_rec:
                parts.append(f"Recommended Standard: {primary_rec['designation']} ({primary_rec['title']}).")
                if primary_rec.get("matched_attributes"):
                    parts.append(f"Grounding: Matched attributes: {', '.join(primary_rec['matched_attributes'])}.")
                parts.append(reg_statement)
            elif rev:
                parts.append(f"Candidate for Expert Review: {rev['designation']} ({rev['title']}).")
                if rev.get("evidence_gaps"):
                    parts.append(f"Evidence Gaps: {', '.join(rev['evidence_gaps'])}.")
            elif clarifications_needed:
                parts.append(f"Clarifications Needed: {' '.join(clarifications_needed)}")
            elif decision_state == "OUTSIDE_PROTOTYPE_COVERAGE":
                parts.append("Current prototype covers BIS Civil Engineering (CED) and Electrotechnical (ETD) standards only.")
            elif decision_state == "NO_CONFIDENT_MATCH":
                parts.append("No sufficiently supported applicable standard was identified from searched BIS catalog.")
            explanation = " ".join(parts)

        return {
            "decision_state": decision_state,
            "primary_recommendation": primary_rec,
            "alternative_standards": alts,
            "review_candidate": rev,
            "clarifications_needed": clarifications_needed or [],
            "clarification_category": clarification_category,
            "normalized_requirements": normalized_requirements or {},
            "lifecycle": life,
            "regulatory": reg,
            "confidence": confidence,
            "uncertainty_statement": AnswerBuilder._derive_uncertainty_statement(decision_state, primary_rec, confidence),
            "provenance": provenance or ["STANDSPEC_PROTOTYPE_CED_ETD_GRAPH_V2_0"],
            "natural_language_explanation": explanation,
        }

    @staticmethod
    def _derive_uncertainty_statement(decision_state: str, primary_rec: Optional[dict], confidence: str) -> str:
        if decision_state == "PRIMARY_RECOMMENDATION_AVAILABLE" and confidence == "HIGH":
            return "Recommendation is verified by matching attributes and verified active lifecycle."
        if decision_state == "CONDITIONAL_RECOMMENDATION":
            return "Recommendation is conditional on site-specific parameters or installation sub-types."
        if decision_state == "MULTIPLE_POSSIBLE_STANDARDS":
            return "Multiple plausible standards exist; technical discriminator required."
        if decision_state == "EXPERT_REVIEW_REQUIRED":
            return "Evidentiary threshold not fully satisfied; expert engineering review required."
        if decision_state == "OUTSIDE_PROTOTYPE_COVERAGE":
            return "Query falls outside Civil Engineering (CED) and Electrotechnical (ETD) indexed coverage."
        return "Insufficient technical parameters or candidate evidence to confirm applicability."
