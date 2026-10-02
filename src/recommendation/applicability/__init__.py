"""
StandSpec AI — Modular Applicability Engine (Phase P1-B)
Exports generic engine, domain rule registries, state enums,
and Phase 4-6 concept modules (material, product, discriminator).
"""

from src.recommendation.applicability.state import ApplicabilityState, AttributeStatus
from src.recommendation.applicability.base_registry import DomainRuleRegistry
from src.recommendation.applicability.ced_registry import CEDRuleRegistry
from src.recommendation.applicability.etd_registry import ETDRuleRegistry
from src.recommendation.applicability.core import GenericApplicabilityEngine
from src.recommendation.applicability.material_concepts import (
    resolve_material,
    resolve_material_compatibility,
    extract_material_from_text,
    MaterialMatchResult,
    MaterialFamily,
    MATERIAL_TAXONOMY,
)
from src.recommendation.applicability.product_concepts import (
    resolve_base_product,
    build_product_signature,
    compare_products,
    detect_product_from_title,
    ProductSignature,
    PRODUCT_FAMILIES,
)
from src.recommendation.applicability.discriminator_policy import (
    get_discriminator_policy,
    get_mandatory_discriminators,
    evaluate_discriminator_coverage,
    DISCRIMINATOR_POLICY,
)

__all__ = [
    "ApplicabilityState",
    "AttributeStatus",
    "DomainRuleRegistry",
    "CEDRuleRegistry",
    "ETDRuleRegistry",
    "GenericApplicabilityEngine",
    "resolve_material",
    "resolve_material_compatibility",
    "extract_material_from_text",
    "MaterialMatchResult",
    "MaterialFamily",
    "MATERIAL_TAXONOMY",
    "resolve_base_product",
    "build_product_signature",
    "compare_products",
    "detect_product_from_title",
    "ProductSignature",
    "PRODUCT_FAMILIES",
    "get_discriminator_policy",
    "get_mandatory_discriminators",
    "evaluate_discriminator_coverage",
    "DISCRIMINATOR_POLICY",
]
