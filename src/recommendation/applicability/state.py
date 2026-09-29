"""
Applicability States and Attribute Status Definitions — StandSpec AI (Phase P1-B)
"""

from enum import Enum


class ApplicabilityState(str, Enum):
    APPLICABLE = "APPLICABLE"
    CONDITIONALLY_APPLICABLE = "CONDITIONALLY_APPLICABLE"
    RELATED = "RELATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"
    EXPERT_REVIEW_REQUIRED = "EXPERT_REVIEW_REQUIRED"


class AttributeStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"
