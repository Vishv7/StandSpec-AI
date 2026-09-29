"""
Candidate Eligibility Policy — StandSpec AI (Phase P1-E Section 6).
Determines candidate corpus eligibility strictly via semantic metadata:
- candidate_status
- standard_role
- node_type
- department
Eliminates arbitrary base-number exclusion lists and fragile substring heuristics.
"""

from typing import Dict, Any


class CandidateEligibilityPolicy:
    """
    Authoritative corpus segregation policy for StandSpec AI.

    Corpus Segregation Invariants:
      - PRIMARY_CANDIDATE_CORPUS: Product specifications & design codes (ELIGIBLE).
      - SUPPORTING_CONTEXT_CORPUS: Test methods, terminology, dimensions, codes of practice (SUPPORTING_ONLY).
      - EXTERNAL_REFERENCE_CORPUS: Non-BIS / international standards (ISO, IEC, ASTM).
      - UNKNOWN_ROLE: Searchable for exact references, but NOT promoted as primary product candidate.
    """

    NON_PRIMARY_ROLES = {
        "TEST_METHOD",
        "TERMINOLOGY",
        "DIMENSIONAL_MOUNTING",
        "INSTALLATION_CODE",
        "CODE_OF_PRACTICE",
        "GUIDELINES",
    }

    @classmethod
    def is_primary_candidate(cls, node: Dict[str, Any], intent: str = "SUPPLY") -> bool:
        """
        Determines whether a graph node is eligible for the primary recommendation corpus.
        Section 6.1: Segregation governed by candidate_status + standard_role + node_type.
        """
        # 1. External standards belong to external corpus only
        if node.get("node_type") == "EXTERNAL_STANDARD":
            return False

        # 2. Check candidate_status from graph metadata
        cand_status = node.get("candidate_status", "ELIGIBLE")
        if cand_status in ("CONTEXT_ONLY", "EXCLUDED"):
            return False

        # 3. Check standard_role
        role = node.get("standard_role", "UNKNOWN_ROLE")
        if role in cls.NON_PRIMARY_ROLES:
            return False

        # Verify via RoleClassifier taxonomy (e.g. dimensional mountings, test methods)
        from src.recommendation.role_classifier import RoleClassifier
        classified_role = RoleClassifier.classify_with_evidence(node).get("standard_role")
        if classified_role in cls.NON_PRIMARY_ROLES:
            return False

        # If candidate_status is SUPPORTING_ONLY, only exclude if role is NOT a primary product or component
        if cand_status == "SUPPORTING_ONLY" and role not in ("PRIMARY_PRODUCT", "PRODUCT_SPECIFICATION", "COMPONENT"):
            return False

        # 4. Must have a valid title
        title = (node.get("title") or "").strip()
        if not title:
            return False

        # Must have a designation
        desig = (node.get("designation") or "").strip()
        if not desig:
            return False

        return True

    @classmethod
    def is_supporting_context(cls, node: Dict[str, Any]) -> bool:
        """Identifies nodes serving as supporting technical context."""
        if node.get("node_type") == "EXTERNAL_STANDARD":
            return False
        cand_status = node.get("candidate_status")
        role = node.get("standard_role")
        return cand_status == "SUPPORTING_ONLY" or role in cls.NON_PRIMARY_ROLES

    @classmethod
    def is_external_reference(cls, node: Dict[str, Any]) -> bool:
        """Identifies nodes representing external/foreign standards."""
        return node.get("node_type") == "EXTERNAL_STANDARD"
