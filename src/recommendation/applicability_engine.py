"""
Technical Applicability Engine — StandSpec AI (Phase P1-B Refactoring)
Maintains 100% backwards compatibility while delegating core matching to
the modular GenericApplicabilityEngine and domain rule registries (CED + ETD).
"""

from src.recommendation.applicability.state import ApplicabilityState, AttributeStatus
from src.recommendation.applicability.base_registry import DomainRuleRegistry
from src.recommendation.applicability.ced_registry import CEDRuleRegistry
from src.recommendation.applicability.etd_registry import ETDRuleRegistry
from src.recommendation.applicability.core import GenericApplicabilityEngine


class TechnicalApplicabilityEngine(GenericApplicabilityEngine):
    """
    Backwards-compatible Technical Applicability Engine.
    Extends GenericApplicabilityEngine pre-configured with CED and ETD domain rule registries.
    """

    def __init__(self, registries=None):
        if registries is None:
            registries = [CEDRuleRegistry(), ETDRuleRegistry()]
        super().__init__(registries=registries)


__all__ = [
    "ApplicabilityState",
    "AttributeStatus",
    "DomainRuleRegistry",
    "CEDRuleRegistry",
    "ETDRuleRegistry",
    "GenericApplicabilityEngine",
    "TechnicalApplicabilityEngine",
]
