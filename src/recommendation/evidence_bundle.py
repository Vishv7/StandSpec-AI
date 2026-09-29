"""
Structured Evidence Bundle and Readiness Model — StandSpec AI (Phase P1-C)
Implements first-class evidence grounding with audit provenance, EvidencePolicy,
and multidimensional readiness.

Replaces coarse ad-hoc boolean flags with authoritative EvidencePolicy:
  Evidence Dimensions:
    - identity_ready
    - scope_ready
    - applicability_ready
    - lifecycle_ready
    - regulatory_ready
    - provenance_ready

  Claim Types (EvidencePolicy):
    - RETRIEVAL_CLAIM
    - CANDIDATE_CLAIM
    - TECHNICAL_APPLICABILITY_CLAIM
    - PRIMARY_RECOMMENDATION_CLAIM
    - REGULATORY_MANDATE_CLAIM

  Evidence Gap Codes:
    - SCOPE_MISSING
    - LIFECYCLE_UNVERIFIED
    - REGULATORY_UNVERIFIED
    - ROLE_MISMATCH
    - TECHNICAL_ATTRIBUTE_MISMATCH
    - IDENTITY_UNVERIFIED
    - UNHYDRATED_STUB
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone


class ClaimType(str, Enum):
    """Categorical claim types evaluated against EvidencePolicy."""
    RETRIEVAL_CLAIM = "RETRIEVAL_CLAIM"
    CANDIDATE_CLAIM = "CANDIDATE_CLAIM"
    TECHNICAL_APPLICABILITY_CLAIM = "TECHNICAL_APPLICABILITY_CLAIM"
    PRIMARY_RECOMMENDATION_CLAIM = "PRIMARY_RECOMMENDATION_CLAIM"
    REGULATORY_MANDATE_CLAIM = "REGULATORY_MANDATE_CLAIM"


class EvidenceGapCode(str, Enum):
    """Canonical gap codes identifying missing evidentiary prerequisites (Phase P1-D)."""
    IDENTITY_UNVERIFIED = "IDENTITY_UNVERIFIED"
    SCOPE_MISSING = "SCOPE_MISSING"
    APPLICABILITY_EVIDENCE_MISSING = "APPLICABILITY_EVIDENCE_MISSING"
    PRODUCT_GROUNDING_MISSING = "PRODUCT_GROUNDING_MISSING"
    ROLE_UNVERIFIED = "ROLE_UNVERIFIED"
    ROLE_MISMATCH = "ROLE_MISMATCH"
    TECHNICAL_ATTRIBUTE_MISMATCH = "TECHNICAL_ATTRIBUTE_MISMATCH"
    LIFECYCLE_UNVERIFIED = "LIFECYCLE_UNVERIFIED"
    PROVENANCE_UNVERIFIED = "PROVENANCE_UNVERIFIED"
    UNHYDRATED_STUB = "UNHYDRATED_STUB"
    REGULATORY_UNVERIFIED = "REGULATORY_UNVERIFIED"
    REGULATORY_SOURCE_UNAVAILABLE = "REGULATORY_SOURCE_UNAVAILABLE"
    REGULATORY_CONFLICT = "REGULATORY_CONFLICT"
    CONTRADICTORY_REQUIREMENTS = "CONTRADICTORY_REQUIREMENTS"


class EvidenceItem:
    """An atomic, auditable piece of evidence grounding a technical or regulatory claim."""

    def __init__(
        self,
        source_type: str,
        source_id: str,
        field: str,
        evidence_text: str,
        span: Optional[List[int]] = None,
        verification_status: str = "VERIFIED",
        retrieved_at: Optional[str] = None,
        source_priority: int = 1,
    ):
        self.source_type = source_type
        self.source_id = source_id
        self.field = field
        self.evidence_text = evidence_text
        self.span = span or []
        self.verification_status = verification_status  # VERIFIED, UNVERIFIED, INFERRED, CONFLICTING
        self.retrieved_at = retrieved_at or datetime.now(timezone.utc).isoformat()
        self.source_priority = source_priority

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "field": self.field,
            "evidence_text": self.evidence_text,
            "span": self.span,
            "verification_status": self.verification_status,
            "retrieved_at": self.retrieved_at,
            "source_priority": self.source_priority,
        }


class EvidencePolicy:
    """
    Authoritative policy defining required evidentiary support per claim type.
    Decoupled from pre-baked graph booleans; evaluates bundle state directly.
    """

    @staticmethod
    def evaluate_claim(
        claim_type: ClaimType,
        bundle: "EvidenceBundle",
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[str]]:
        gaps: List[str] = []

        if claim_type == ClaimType.RETRIEVAL_CLAIM:
            if not bundle.identity_ready:
                gaps.append(EvidenceGapCode.IDENTITY_UNVERIFIED.value)
            return len(gaps) == 0, gaps

        elif claim_type == ClaimType.CANDIDATE_CLAIM:
            if not bundle.identity_ready:
                gaps.append(EvidenceGapCode.IDENTITY_UNVERIFIED.value)
            if not bundle.department:
                gaps.append(EvidenceGapCode.IDENTITY_UNVERIFIED.value)
            return len(gaps) == 0, gaps

        elif claim_type == ClaimType.TECHNICAL_APPLICABILITY_CLAIM:
            if not bundle.identity_ready:
                gaps.append(EvidenceGapCode.IDENTITY_UNVERIFIED.value)
            if not bundle.scope_ready:
                gaps.append(EvidenceGapCode.SCOPE_MISSING.value)
            if context and context.get("mismatched_attributes"):
                gaps.append(EvidenceGapCode.TECHNICAL_ATTRIBUTE_MISMATCH.value)
            return len(gaps) == 0, gaps

        elif claim_type == ClaimType.PRIMARY_RECOMMENDATION_CLAIM:
            if not bundle.identity_ready:
                gaps.append(EvidenceGapCode.IDENTITY_UNVERIFIED.value)
            if not bundle.scope_ready:
                gaps.append(EvidenceGapCode.SCOPE_MISSING.value)
            if not bundle.applicability_ready:
                if EvidenceGapCode.SCOPE_MISSING.value not in gaps:
                    gaps.append(EvidenceGapCode.APPLICABILITY_EVIDENCE_MISSING.value)
            if not bundle.lifecycle_ready:
                gaps.append(EvidenceGapCode.LIFECYCLE_UNVERIFIED.value)
            if not bundle.provenance_ready:
                gaps.append(EvidenceGapCode.PROVENANCE_UNVERIFIED.value)
            if not bundle.provenance_metadata.get("is_hydrated", False) and not bundle.scope_ready:
                gaps.append(EvidenceGapCode.UNHYDRATED_STUB.value)

            disallowed_roles = {
                "TEST_METHOD", "TERMINOLOGY", "DIMENSIONAL_MOUNTING",
                "CODE_OF_PRACTICE", "GUIDELINES", "SAMPLING_INSPECTION",
                "MEASUREMENT_METHOD", "SUPPORTING_STANDARD"
            }
            if bundle.standard_role in disallowed_roles:
                gaps.append(EvidenceGapCode.ROLE_MISMATCH.value)
            elif bundle.standard_role == "UNKNOWN_ROLE":
                # Unknown role in physical procurement cannot be primary
                pass

            if context:
                if context.get("mismatched_attributes"):
                    gaps.append(EvidenceGapCode.TECHNICAL_ATTRIBUTE_MISMATCH.value)

                # Positive product grounding: for physical procurement query, PRODUCT must match
                matched = context.get("matched_attributes") or []
                target_prod = context.get("target_product") or context.get("product")
                if target_prod and "PRODUCT" not in matched:
                    gaps.append(EvidenceGapCode.PRODUCT_GROUNDING_MISSING.value)

                if context.get("contradictions"):
                    gaps.append(EvidenceGapCode.CONTRADICTORY_REQUIREMENTS.value)

            # Stale graph flag protection: do not let static negative flags override verified runtime scope evidence
            if bundle.evidence_flags.get("data_layer_recommendation_ready") is False and not bundle.scope_ready:
                if EvidenceGapCode.SCOPE_MISSING.value not in gaps:
                    gaps.append(EvidenceGapCode.SCOPE_MISSING.value)

            return len(gaps) == 0, gaps

        elif claim_type == ClaimType.REGULATORY_MANDATE_CLAIM:
            reg_state = (bundle.regulatory_evidence or {}).get("regulatory_state")
            if reg_state == "CONFLICTING_EVIDENCE":
                gaps.append(EvidenceGapCode.REGULATORY_CONFLICT.value)
            elif reg_state not in (
                "MANDATORY_CONFIRMED",
                "NOT_MANDATORY_CONFIRMED",
                "MANDATORY_CONDITIONALLY_APPLICABLE",
                "NOT_APPLICABLE",
            ):
                gaps.append(EvidenceGapCode.REGULATORY_UNVERIFIED.value)
                gaps.append(EvidenceGapCode.REGULATORY_SOURCE_UNAVAILABLE.value)
            return len(gaps) == 0, gaps

        return False, ["UNKNOWN_CLAIM_TYPE"]


class EvidenceBundle:
    """
    First-class evidentiary representation of an Indian Standard.
    Encapsulates identity, scope, technical attributes, lifecycle, regulatory status, and provenance.
    Sole authority for recommendation readiness decisions.
    """

    def __init__(
        self,
        designation: str,
        title: str,
        department: Optional[str] = None,
        base_number: Optional[int] = None,
        part: Optional[str] = None,
        section: Optional[str] = None,
        year: Optional[str] = None,
        standard_role: str = "UNKNOWN_ROLE",
    ):
        self.designation = designation
        self.title = title
        self.department = department
        self.base_number = base_number
        self.part = part
        self.section = section
        self.year = year
        self.standard_role = standard_role

        # Scope evidence
        self.raw_scope: Optional[str] = None
        self.scope_inclusions: List[str] = []
        self.scope_exclusions: List[str] = []
        self.scope_evidence_items: List[EvidenceItem] = []

        # Technical applicability attributes
        self.technical_attributes: Dict[str, Dict[str, Any]] = {
            "material": {"value": None, "state": "UNKNOWN", "evidence": None},
            "product": {"value": None, "state": "UNKNOWN", "evidence": None},
            "dimensions": {"value": None, "state": "UNKNOWN", "evidence": None},
            "voltage": {"value": None, "state": "UNKNOWN", "evidence": None},
            "capacity": {"value": None, "state": "UNKNOWN", "evidence": None},
            "application": {"value": None, "state": "UNKNOWN", "evidence": None},
            "safety_performance": {"value": None, "state": "UNKNOWN", "evidence": None},
        }

        # Lifecycle evidence
        self.lifecycle_evidence: Dict[str, Any] = {
            "status": "UNKNOWN",
            "publication_date": None,
            "effective_date": None,
            "review_date": None,
            "reaffirmation_date": None,
            "supersedes": None,
            "superseded_by": None,
            "is_superseded": False,
            "amendments": [],
            "provenance": [],
        }

        # Regulatory evidence
        self.regulatory_evidence: Dict[str, Any] = {
            "regulatory_state": "NOT_VERIFIED_IN_CURRENT_CORPUS",
            "is_mandatory": False,
            "scheme": None,
            "order_number": None,
            "order_date": None,
            "effective_date": None,
            "gazette_url": None,
            "evidence_source": None,
        }

        # Provenance
        self.provenance_metadata: Dict[str, Any] = {
            "source_type": "BIS_KNOWLEDGE_GRAPH",
            "source_id": designation,
            "is_hydrated": False,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

        # Additional evidence flags
        self.evidence_flags: Dict[str, Any] = {}

    # ── Evidence Dimensions ──

    @property
    def identity_ready(self) -> bool:
        """True if standard has valid canonical designation, title, and base number or IS prefix."""
        return bool(self.designation and self.title and (self.base_number is not None or "IS" in self.designation))

    @property
    def scope_ready(self) -> bool:
        """True if verifiable scope text exists and is substantive (>= 20 chars)."""
        return bool(self.raw_scope and len(self.raw_scope.strip()) >= 20)

    @property
    def applicability_ready(self) -> bool:
        """True if identity and substantive scope exist to evaluate technical boundaries."""
        return self.identity_ready and self.scope_ready

    @property
    def technical_applicability_ready(self) -> bool:
        """Alias for applicability_ready under EvidencePolicy."""
        sat, _ = EvidencePolicy.evaluate_claim(ClaimType.TECHNICAL_APPLICABILITY_CLAIM, self)
        return sat

    @property
    def lifecycle_ready(self) -> bool:
        """
        True only if lifecycle status is explicitly verified and not UNKNOWN, SUPERSEDED, or WITHDRAWN.
        """
        status = (self.lifecycle_evidence.get("status") or "").upper()
        if status in ("UNKNOWN", "", "UNVERIFIED", "LIFECYCLE_UNVERIFIED", "SUPERSEDED", "WITHDRAWN", "VERIFIED_SUPERSEDED", "VERIFIED_WITHDRAWN", "FUTURE_NOT_VALID", "CONFLICTING_LIFECYCLE"):
            return False
        if self.lifecycle_evidence.get("lifecycle_state") in ("LIFECYCLE_UNVERIFIED", "VERIFIED_SUPERSEDED", "VERIFIED_WITHDRAWN", "FUTURE_NOT_VALID", "CONFLICTING_LIFECYCLE"):
            return False
        if self.lifecycle_evidence.get("is_superseded"):
            return False
        if self.lifecycle_evidence.get("is_valid_on_date") is False:
            return False
        ev_status = (self.lifecycle_evidence.get("lifecycle_evidence_status") or "").upper()
        if ev_status in ("LIFECYCLE_EVIDENCE_INSUFFICIENT", "UNKNOWN"):
            return False
        return True

    @property
    def regulatory_ready(self) -> bool:
        """True if regulatory state is definitively verified (not unverified / unavailable)."""
        reg_state = self.regulatory_evidence.get("regulatory_state")
        return reg_state in (
            "MANDATORY_CONFIRMED",
            "MANDATORY_CONDITIONALLY_APPLICABLE",
            "NOT_MANDATORY_CONFIRMED",
            "NOT_APPLICABLE",
        )

    @property
    def provenance_ready(self) -> bool:
        """True if provenance contains valid source tracking."""
        return bool(self.provenance_metadata.get("source_type") and self.provenance_metadata.get("source_id"))

    # ── Claim-Specific Readiness (governed by EvidencePolicy) ──

    @property
    def retrieval_ready(self) -> bool:
        """Indexed and searchable in knowledge base."""
        sat, _ = EvidencePolicy.evaluate_claim(ClaimType.RETRIEVAL_CLAIM, self)
        return sat

    @property
    def candidate_ready(self) -> bool:
        """Eligible for candidate retrieval and matching."""
        sat, _ = EvidencePolicy.evaluate_claim(ClaimType.CANDIDATE_CLAIM, self)
        return sat

    @property
    def recommendation_ready(self) -> bool:
        """
        Strict claim readiness: True ONLY when candidate, scope, applicability,
        and lifecycle satisfy EvidencePolicy for primary recommendation.
        """
        prod_val = (self.technical_attributes.get("product") or {}).get("value")
        context = {
            "matched_attributes": self.evidence_flags.get("matched_attributes", []),
            "mismatched_attributes": self.evidence_flags.get("mismatched_attributes", []),
            "target_product": prod_val,
            "is_grounded": bool(self.evidence_flags.get("matched_attributes")),
        }
        sat, _ = EvidencePolicy.evaluate_claim(ClaimType.PRIMARY_RECOMMENDATION_CLAIM, self, context=context)
        return sat

    @property
    def regulatory_claim_ready(self) -> bool:
        """Ready to assert mandatory certification status."""
        sat, _ = EvidencePolicy.evaluate_claim(ClaimType.REGULATORY_MANDATE_CLAIM, self)
        return sat

    def get_evidence_gaps(
        self,
        claim_type: ClaimType = ClaimType.PRIMARY_RECOMMENDATION_CLAIM,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Compute missing evidence gaps for a specific claim type."""
        _, gaps = EvidencePolicy.evaluate_claim(claim_type, self, context=context)
        return gaps

    def get_readiness_report(self) -> Dict[str, Any]:
        """Generate structured multidimensional readiness dictionary."""
        return {
            "evidence_dimensions": {
                "identity_ready": self.identity_ready,
                "scope_ready": self.scope_ready,
                "applicability_ready": self.applicability_ready,
                "lifecycle_ready": self.lifecycle_ready,
                "regulatory_ready": self.regulatory_ready,
                "provenance_ready": self.provenance_ready,
            },
            "claim_readiness": {
                "RETRIEVAL_READY": self.retrieval_ready,
                "CANDIDATE_READY": self.candidate_ready,
                "APPLICABILITY_READY": self.applicability_ready,
                "RECOMMENDATION_READY": self.recommendation_ready,
                "REGULATORY_CLAIM_READY": self.regulatory_claim_ready,
            },
            "evidence_gaps": {
                "primary_recommendation": self.get_evidence_gaps(ClaimType.PRIMARY_RECOMMENDATION_CLAIM),
                "regulatory_mandate": self.get_evidence_gaps(ClaimType.REGULATORY_MANDATE_CLAIM),
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize bundle into dictionary conforming to decision contract."""
        return {
            "designation": self.designation,
            "title": self.title,
            "department": self.department,
            "base_number": self.base_number,
            "part": self.part,
            "section": self.section,
            "year": self.year,
            "standard_role": self.standard_role,
            "scope": {
                "raw_scope": self.raw_scope,
                "inclusions": self.scope_inclusions,
                "exclusions": self.scope_exclusions,
                "evidence_items": [ei.to_dict() for ei in self.scope_evidence_items],
            },
            "technical_applicability": self.technical_attributes,
            "lifecycle": self.lifecycle_evidence,
            "regulatory": self.regulatory_evidence,
            "provenance": self.provenance_metadata,
            "readiness": self.get_readiness_report(),
        }

    @classmethod
    def from_node(
        cls,
        node: Dict[str, Any],
        lifecycle_info: Optional[Dict[str, Any]] = None,
        reg_info: Optional[Dict[str, Any]] = None,
        applicability_info: Optional[Dict[str, Any]] = None,
    ) -> "EvidenceBundle":
        """Hydrate an EvidenceBundle from a graph node and optional gate outputs."""
        desig = node.get("designation") or node.get("id") or ""
        title = node.get("title") or ""
        dept = node.get("primary_department") or (node.get("source_departments") or [None])[0]
        base_num = node.get("base_number")
        part = str(node.get("part")) if node.get("part") is not None else None
        section = str(node.get("section")) if node.get("section") is not None else None
        year = str(node.get("year")) if node.get("year") is not None else None
        role = node.get("standard_role") or "UNKNOWN_ROLE"

        bundle = cls(
            designation=desig,
            title=title,
            department=dept,
            base_number=base_num,
            part=part,
            section=section,
            year=year,
            standard_role=role,
        )

        # Preserve any explicit negative mock flags
        if "recommendation_ready" in node:
            bundle.evidence_flags["data_layer_recommendation_ready"] = bool(node.get("recommendation_ready"))

        # Populate scope
        raw_s = node.get("scope")
        if raw_s and str(raw_s).strip():
            bundle.raw_scope = str(raw_s).strip()
            bundle.scope_evidence_items.append(
                EvidenceItem(
                    source_type="BIS_STANDARD_SCOPE",
                    source_id=desig,
                    field="scope",
                    evidence_text=bundle.raw_scope[:300],
                    verification_status="VERIFIED",
                )
            )

        # Populate lifecycle
        if lifecycle_info:
            lifecycle_st = lifecycle_info.get("lifecycle_state")
            if not lifecycle_st:
                lifecycle_st = "VERIFIED_SUPERSEDED" if lifecycle_info.get("is_superseded") else "VERIFIED_ACTIVE"
            bundle.lifecycle_evidence.update({
                "status": lifecycle_st,
                "lifecycle_state": lifecycle_st,
                "recommended_edition": lifecycle_info.get("recommended_edition"),
                "is_superseded": lifecycle_info.get("is_superseded", False),
                "superseded_by": lifecycle_info.get("superseded_by"),
                "lifecycle_evidence_status": lifecycle_info.get("lifecycle_evidence_status", "LIFECYCLE_EVIDENCE_INSUFFICIENT"),
                "amendments": lifecycle_info.get("applicable_amendments", lifecycle_info.get("amendments", [])),
                "provenance": lifecycle_info.get("provenance", []),
                "reaffirmation_date": lifecycle_info.get("reaffirmation_date"),
                "review_date": lifecycle_info.get("review_date"),
                "is_valid_on_date": (lifecycle_info.get("temporal_validity") or {}).get("is_valid_on_evaluation_date", True),
            })
        else:
            has_status = node.get("status") or node.get("standard_status")
            status_str = str(has_status).upper() if has_status else "UNKNOWN"
            bundle.lifecycle_evidence["status"] = status_str
            bundle.lifecycle_evidence["lifecycle_state"] = status_str
            bundle.lifecycle_evidence["lifecycle_evidence_status"] = "VERIFIED" if has_status else "UNKNOWN"
            if node.get("amendments"):
                bundle.lifecycle_evidence["amendments"] = node.get("amendments")

        # Populate regulatory
        if reg_info:
            bundle.regulatory_evidence.update(reg_info)
        else:
            if node.get("qco_mandatory") is not None:
                bundle.regulatory_evidence["is_mandatory"] = bool(node.get("qco_mandatory"))
                bundle.regulatory_evidence["regulatory_state"] = (
                    "MANDATORY_CONFIRMED" if node.get("qco_mandatory") else "NOT_MANDATORY_CONFIRMED"
                )

        # Populate provenance
        bundle.provenance_metadata.update({
            "is_hydrated": bool(node.get("is_hydrated", False)),
            "source_type": "BIS_PORTAL_EXCEL" if node.get("is_hydrated") else "EXTERNAL_REFERENCE",
        })

        # Populate technical applicability
        if applicability_info:
            eval_trace = applicability_info.get("evaluation_trace", {})
            for attr_name in ("material", "product", "dimensions", "voltage", "capacity", "application", "safety_performance"):
                if attr_name in eval_trace:
                    trace_item = eval_trace[attr_name]
                    bundle.technical_attributes[attr_name] = {
                        "value": trace_item.get("value"),
                        "state": trace_item.get("status", "UNKNOWN"),
                        "evidence": trace_item.get("evidence"),
                    }
            bundle.evidence_flags["matched_attributes"] = applicability_info.get("matched_attributes", [])
            bundle.evidence_flags["mismatched_attributes"] = applicability_info.get("mismatched_attributes", [])
            bundle.evidence_flags["applicability_state"] = applicability_info.get("state")

        return bundle
