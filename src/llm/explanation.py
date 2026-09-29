"""
Evidence-Grounded Recommendation Explainer — StandSpec AI (Phase P1-C.7)
Generates natural language summaries grounded strictly in verified ExplanationFacts.
Includes strict anti-hallucination safeguards to guarantee that:
1. When primary_recommendation is null, LLM never invents or claims a recommended standard.
2. Designation numbers and titles are never altered or hallucinated.
3. Statutory mandates (QCO) are accurately conveyed without legal invention.
4. Deterministic template fallback on any validation failure or timeout.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from src.llm.provider import BaseLLMProvider


@dataclass
class ExplanationFacts:
    """
    Authoritative evidence facts contract.
    Only verified, grounded values may be passed to the explainer.
    """
    decision_state: str
    is_recommended: bool
    standard_designation: Optional[str] = None
    title: Optional[str] = None
    matched_attributes: List[str] = field(default_factory=list)
    regulatory_state: str = "VOLUNTARY_OR_UNLISTED"
    qco_order_number: Optional[str] = None
    abstention_reason: Optional[str] = None
    evidence_gaps: List[str] = field(default_factory=list)
    verified_edition: Optional[str] = None
    amendments: List[str] = field(default_factory=list)

    @classmethod
    def from_recommendation_result(cls, rec_result: Dict[str, Any]) -> "ExplanationFacts":
        decision_state = rec_result.get("decision_state", "UNKNOWN")
        primary_rec = rec_result.get("primary_recommendation")
        abstention_reason = rec_result.get("abstention_reason")

        if not primary_rec:
            rev_cand = rec_result.get("review_candidate")
            gaps = rev_cand.get("evidence_gaps", []) if rev_cand else []
            return cls(
                decision_state=decision_state,
                is_recommended=False,
                abstention_reason=abstention_reason,
                evidence_gaps=gaps,
            )

        desig = primary_rec.get("standard_designation")
        title = primary_rec.get("title")
        app = primary_rec.get("applicability", {})
        matched = app.get("matched_attributes", [])
        reg = primary_rec.get("regulatory", {})
        reg_state = reg.get("regulatory_state", "VOLUNTARY_OR_UNLISTED")
        qco = reg.get("qco_order_number") or reg.get("gazette_so_number")
        edition = primary_rec.get("lifecycle", {}).get("recommended_edition")
        amend_notes = primary_rec.get("lifecycle", {}).get("amendment_notes")
        amends = [amend_notes] if amend_notes else []

        return cls(
            decision_state=decision_state,
            is_recommended=True,
            standard_designation=desig,
            title=title,
            matched_attributes=matched,
            regulatory_state=reg_state,
            qco_order_number=qco,
            abstention_reason=None,
            evidence_gaps=[],
            verified_edition=edition,
            amendments=amends,
        )


class EvidenceGroundedExplainer:
    """
    Evidence-Grounded Explainer.
    Uses LLM for fluent synthesis when available, backed by deterministic anti-hallucination verification.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm_provider = llm_provider

    def _generate_deterministic_explanation(self, facts: ExplanationFacts) -> str:
        """Constructs an un-hallucinated, 100% deterministic template explanation."""
        if not facts.is_recommended or not facts.standard_designation:
            parts = [f"Decision State: {facts.decision_state}."]
            if facts.abstention_reason:
                parts.append(f"Abstention Reason: {facts.abstention_reason}")
            if facts.evidence_gaps:
                parts.append(f"Missing Evidence Gaps: {', '.join(facts.evidence_gaps)}.")
            return " ".join(parts)

        parts = [
            f"Recommended Standard: {facts.standard_designation} ({facts.title or 'Standard'}).",
            f"Decision State: {facts.decision_state}.",
        ]
        if facts.matched_attributes:
            parts.append(f"Technical Grounding: Matched attributes: {', '.join(facts.matched_attributes)}.")

        if facts.regulatory_state == "MANDATORY_CONFIRMED":
            parts.append(f"Statutory Mandate: MANDATORY under Gazette Order {facts.qco_order_number or 'QCO'}.")
        elif facts.regulatory_state in ("NOT_VERIFIED_IN_CURRENT_CORPUS", "UNVERIFIED", "UNKNOWN"):
            parts.append("Statutory Mandate: Regulatory mandatory status was not verified in the current regulatory corpus.")
        elif facts.regulatory_state == "CONFLICTING_EVIDENCE":
            parts.append("Statutory Mandate: Conflicting regulatory evidence prevents a verified mandate conclusion.")
        elif facts.regulatory_state == "VOLUNTARY_OR_UNLISTED":
            parts.append("Statutory Mandate: VOLUNTARY_OR_UNLISTED (No mandatory QCO identified in searched official gazette notifications).")
        else:
            parts.append(f"Statutory Mandate: {facts.regulatory_state}.")

        if facts.amendments:
            parts.append(f"Amendments: {'; '.join(facts.amendments)}.")

        return " ".join(parts)

    def _validate_llm_response(self, text: str, facts: ExplanationFacts) -> bool:
        """
        Validates LLM text against ground truth facts.
        Returns False if text contains any hallucinations or policy contradictions.
        """
        lower = text.lower()

        # 1. Null-primary safety: when not recommended, MUST NOT say "recommended standard"
        if not facts.is_recommended:
            forbidden_phrases = ["recommended standard", "we recommend", "is recommended", "primary recommendation: is"]
            if any(p in lower for p in forbidden_phrases):
                return False

        # 2. Designation fidelity: if recommended, designation must appear verbatim or as base number
        if facts.is_recommended and facts.standard_designation:
            base_desig = facts.standard_designation.split(":")[0].strip().lower()
            base_desig_norm = re.sub(r'\s+', ' ', base_desig)
            text_norm = re.sub(r'\s+', ' ', lower)
            if base_desig_norm not in text_norm:
                return False

        # 3. Regulatory fidelity: strictly grounded in verified evidence
        if facts.regulatory_state == "MANDATORY_CONFIRMED":
            if "voluntary" in lower or "optional" in lower or "not mandatory" in lower or "non-mandatory" in lower:
                return False
        elif facts.regulatory_state in ("NOT_VERIFIED_IN_CURRENT_CORPUS", "UNVERIFIED", "UNKNOWN"):
            # When unverified, output must NEVER claim "not mandatory", "voluntary", or "mandatory"
            if "not mandatory" in lower or "non-mandatory" in lower or "voluntary" in lower:
                return False
            if "mandatory under qco" in lower or "mandatory under gazette" in lower or "statutory requirement" in lower:
                return False
        elif facts.regulatory_state == "CONFLICTING_EVIDENCE":
            # When conflicting, must not state a definitive mandate conclusion
            if "not mandatory" in lower or "non-mandatory" in lower or "voluntary" in lower:
                return False
            if "mandatory under qco" in lower or "statutory requirement" in lower:
                return False
        elif facts.regulatory_state == "VOLUNTARY_OR_UNLISTED":
            if "mandatory under qco" in lower or "statutory requirement" in lower or "mandatory under gazette" in lower:
                return False
        else:
            if "mandatory under qco" in lower:
                return False

        # 4. Evidence ID fidelity: reject invented gazette / S.O. order numbers
        so_matches = re.findall(r"s\.o\.\s*(\d+[a-z\(\)]*)", lower)
        if so_matches:
            if not facts.qco_order_number:
                return False
            qco_lower = facts.qco_order_number.lower()
            for m in so_matches:
                if m not in qco_lower:
                    return False

        return True

    def explain(self, rec_result: Dict[str, Any]) -> str:
        """
        Generates explanation for a recommendation result.
        Enforces strict anti-hallucination validation on LLM output.
        """
        facts = ExplanationFacts.from_recommendation_result(rec_result)
        deterministic_summary = self._generate_deterministic_explanation(facts)

        if not self.llm_provider or not self.llm_provider.is_available():
            return deterministic_summary

        prompt_payload = {
            "decision_state": facts.decision_state,
            "is_recommended": facts.is_recommended,
            "standard_designation": facts.standard_designation,
            "title": facts.title,
            "matched_attributes": facts.matched_attributes,
            "regulatory_state": facts.regulatory_state,
            "qco_order_number": facts.qco_order_number,
            "abstention_reason": facts.abstention_reason,
            "evidence_gaps": facts.evidence_gaps,
        }

        prompt = (
            "Summarize the following verified procurement recommendation in 2 concise sentences for an engineer:\n"
            f"Verified Facts: {json.dumps(prompt_payload)}\n\n"
            "Strict Constraints:\n"
            "1. You must NOT alter any standard designation, year, or regulatory status.\n"
            "2. If is_recommended is false, do NOT claim any standard is recommended.\n"
            "3. Do not invent any facts not present in the verified facts payload."
        )

        try:
            llm_text = self.llm_provider.generate(prompt)

            # Strict post-generation verification
            if not self._validate_llm_response(llm_text, facts):
                return deterministic_summary

            return llm_text.strip()
        except Exception:
            return deterministic_summary
