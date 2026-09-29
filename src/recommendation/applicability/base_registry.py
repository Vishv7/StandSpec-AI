"""
Domain Rule Registry Abstract Interface — StandSpec AI (Phase P1-B)
Allows domain-specific rules (CED for Civil, ETD for Electrotechnical)
to be cleanly plugged into the Generic Applicability Engine without coupling
core matching logic to specific Indian Standard families.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Callable
from src.recommendation.applicability.state import AttributeStatus


class DomainRuleRegistry(ABC):
    """
    Abstract plugin for department-specific applicability rules.
    """

    @property
    @abstractmethod
    def department_code(self) -> str:
        """e.g. 'CED' or 'ETD'"""
        pass

    @abstractmethod
    def get_product_stem_mappings(self) -> Dict[str, List[str]]:
        """Returns map of normalized product names to search stems."""
        pass

    @abstractmethod
    def get_scope_boundaries(self) -> List[Dict[str, Any]]:
        """
        Returns list of boundary exclusion rules:
        [{"standard_family": "...", "attribute": "...", "exclusion_rule": callable, "reason": "..."}]
        """
        pass

    def evaluate_custom_attribute(
        self,
        attribute_name: str,
        standard_desig: str,
        req_val: Any,
        cand_doc: Dict[str, Any],
        req_obj: Dict[str, Any],
    ) -> Optional[AttributeStatus]:
        """
        Optional domain override or specific check for an attribute.
        Returns None if default generic matcher should handle it.
        """
        return None

    def check_custom_contradiction(
        self,
        standard_desig: str,
        cand_doc: Dict[str, Any],
        req_obj: Dict[str, Any],
    ) -> Optional[Tuple[bool, str]]:
        """
        Optional domain-level contradiction check.
        Returns (True, reason) if a domain contradiction is detected, else None.
        """
        return None
