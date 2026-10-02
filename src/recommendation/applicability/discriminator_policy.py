"""
Required Discriminator Policy — StandSpec AI (Phase 6, Checkpoint 2)
PS 26108 §9: Product-family-specific discriminator requirements.

Defines which technical attributes are MANDATORY vs OPTIONAL for each
product family to make an unambiguous recommendation decision.

When MANDATORY discriminators are missing AND the result is ambiguous,
the system should abstain rather than guess.
"""

from typing import Dict, Any, List, Optional, Set


class DiscriminatorLevel:
    MANDATORY_FOR_DECISION = "MANDATORY_FOR_DECISION"
    IMPORTANT_FOR_DISAMBIGUATION = "IMPORTANT_FOR_DISAMBIGUATION"
    OPTIONAL_CONTEXT = "OPTIONAL_CONTEXT"


# ── Per-Product-Family Discriminator Policy ──
# Each product family defines which attributes are critical for disambiguation.

DISCRIMINATOR_POLICY: Dict[str, Dict[str, List[str]]] = {
    # ── CED Products ──
    "pipe": {
        DiscriminatorLevel.MANDATORY_FOR_DECISION: ["material", "application"],
        DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION: ["pressure_class", "diameter", "standard_class"],
        DiscriminatorLevel.OPTIONAL_CONTEXT: ["installation_type", "joint_type", "temperature_range"],
    },
    "fitting": {
        DiscriminatorLevel.MANDATORY_FOR_DECISION: ["material", "pipe_type"],
        DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION: ["joint_type", "pressure_class"],
        DiscriminatorLevel.OPTIONAL_CONTEXT: ["diameter_range"],
    },
    "valve": {
        DiscriminatorLevel.MANDATORY_FOR_DECISION: ["valve_type", "material"],
        DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION: ["pressure_class", "diameter"],
        DiscriminatorLevel.OPTIONAL_CONTEXT: ["actuation_type"],
    },
    "cement": {
        DiscriminatorLevel.MANDATORY_FOR_DECISION: ["cement_type"],
        DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION: ["grade"],
        DiscriminatorLevel.OPTIONAL_CONTEXT: ["application"],
    },
    "rebar": {
        DiscriminatorLevel.MANDATORY_FOR_DECISION: ["grade"],
        DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION: ["diameter", "length"],
        DiscriminatorLevel.OPTIONAL_CONTEXT: ["coating"],
    },
    "glass": {
        DiscriminatorLevel.MANDATORY_FOR_DECISION: ["glass_type", "application"],
        DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION: ["thickness", "treatment"],
        DiscriminatorLevel.OPTIONAL_CONTEXT: ["tint", "coating"],
    },

    # ── ETD Products ──
    "cable": {
        DiscriminatorLevel.MANDATORY_FOR_DECISION: ["voltage", "insulation"],
        DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION: ["conductor", "cross_section", "cores"],
        DiscriminatorLevel.OPTIONAL_CONTEXT: ["installation_type", "armour_type", "sheath"],
    },
    "conductor": {
        DiscriminatorLevel.MANDATORY_FOR_DECISION: ["conductor_type", "material"],
        DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION: ["cross_section", "stranding"],
        DiscriminatorLevel.OPTIONAL_CONTEXT: ["coating"],
    },
    "transformer": {
        DiscriminatorLevel.MANDATORY_FOR_DECISION: ["voltage_ratio"],
        DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION: ["power_rating", "type", "cooling"],
        DiscriminatorLevel.OPTIONAL_CONTEXT: ["tap_changer", "vector_group"],
    },
    "switchgear": {
        DiscriminatorLevel.MANDATORY_FOR_DECISION: ["voltage_class", "equipment_type"],
        DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION: ["current_rating", "breaking_capacity"],
        DiscriminatorLevel.OPTIONAL_CONTEXT: ["mounting_type", "enclosure"],
    },
    "meter": {
        DiscriminatorLevel.MANDATORY_FOR_DECISION: ["meter_type"],
        DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION: ["accuracy_class", "voltage", "current_rating"],
        DiscriminatorLevel.OPTIONAL_CONTEXT: ["communication", "phase"],
    },
    "luminaire": {
        DiscriminatorLevel.MANDATORY_FOR_DECISION: ["light_source", "application"],
        DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION: ["wattage", "ip_rating"],
        DiscriminatorLevel.OPTIONAL_CONTEXT: ["colour_temperature", "mounting_type"],
    },
}


def get_discriminator_policy(base_product: str) -> Optional[Dict[str, List[str]]]:
    """Get the discriminator policy for a given base product type."""
    return DISCRIMINATOR_POLICY.get(base_product)


def get_mandatory_discriminators(base_product: str) -> List[str]:
    """Get the mandatory discriminators for a given base product type."""
    policy = DISCRIMINATOR_POLICY.get(base_product, {})
    return policy.get(DiscriminatorLevel.MANDATORY_FOR_DECISION, [])


def evaluate_discriminator_coverage(
    base_product: str,
    available_attributes: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate how many discriminators are available for a given product family.

    Returns:
        Dict with:
          - mandatory_present: list of present mandatory discriminators
          - mandatory_missing: list of missing mandatory discriminators
          - important_present: list of present important discriminators
          - important_missing: list of missing important discriminators
          - coverage_sufficient: bool — True if all mandatory discriminators present
          - should_abstain: bool — True if mandatory discriminators missing AND ambiguity exists
    """
    policy = DISCRIMINATOR_POLICY.get(base_product)
    if not policy:
        return {
            "mandatory_present": [],
            "mandatory_missing": [],
            "important_present": [],
            "important_missing": [],
            "coverage_sufficient": True,  # No policy → no mandatory requirements
            "should_abstain": False,
            "policy_exists": False,
        }

    mandatory = set(policy.get(DiscriminatorLevel.MANDATORY_FOR_DECISION, []))
    important = set(policy.get(DiscriminatorLevel.IMPORTANT_FOR_DISAMBIGUATION, []))

    attr_keys = set()
    for k, v in available_attributes.items():
        if v is not None and v != "" and v != {}:
            attr_keys.add(k.lower())
            # Also add value-based keys for structured attributes
            if isinstance(v, dict) and v.get("value"):
                attr_keys.add(k.lower())

    mandatory_present = [d for d in mandatory if d in attr_keys]
    mandatory_missing = [d for d in mandatory if d not in attr_keys]
    important_present = [d for d in important if d in attr_keys]
    important_missing = [d for d in important if d not in attr_keys]

    coverage_sufficient = len(mandatory_missing) == 0
    # Abstain when mandatory discriminators are missing
    should_abstain = not coverage_sufficient

    return {
        "mandatory_present": mandatory_present,
        "mandatory_missing": mandatory_missing,
        "important_present": important_present,
        "important_missing": important_missing,
        "coverage_sufficient": coverage_sufficient,
        "should_abstain": should_abstain,
        "policy_exists": True,
    }
