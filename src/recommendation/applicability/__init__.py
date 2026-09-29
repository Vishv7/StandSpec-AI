"""
StandSpec AI — Modular Applicability Engine (Phase P1-B)
Exports generic engine, domain rule registries, and state enums.
"""

from src.recommendation.applicability.state import ApplicabilityState, AttributeStatus
from src.recommendation.applicability.base_registry import DomainRuleRegistry
from src.recommendation.applicability.ced_registry import CEDRuleRegistry
from src.recommendation.applicability.etd_registry import ETDRuleRegistry
from src.recommendation.applicability.core import GenericApplicabilityEngine

__all__ = [
    "ApplicabilityState",
    "AttributeStatus",
    "DomainRuleRegistry",
    "CEDRuleRegistry",
    "ETDRuleRegistry",
    "GenericApplicabilityEngine",
]
