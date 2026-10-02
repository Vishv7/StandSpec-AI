"""
Product Family Matching — StandSpec AI (Phase 5, Checkpoint 2)
PS 26108 §8: Structured product representation with family hierarchy.

Replaces generic noun-overlap matching with structured product signatures.
Each product has:
  - base_product: fundamental product type ("pipe", "cable", "transformer")
  - product_family: refined family ("pressure_pipe", "power_cable")
  - subtype: specific product subtype (optional)
  - material: linked material canonical name (optional)
  - application: usage context (optional)
  - modifiers: additional technical modifiers

Product families prevent false matches between related-but-distinct products
(e.g., pipe vs fitting, cable vs conductor, transformer vs switchgear).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set
import re


class ProductMatchResult:
    """Result of product family comparison."""
    def __init__(self, match_type: str, confidence: float, reason: str):
        self.match_type = match_type  # MATCH, MISMATCH, RELATED, UNKNOWN
        self.confidence = confidence
        self.reason = reason

    def to_dict(self):
        return {
            "match_type": self.match_type,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass
class ProductSignature:
    """Structured representation of a procurement product."""
    base_product: str                     # "pipe", "cable", "transformer"
    product_family: str = ""              # "pressure_pipe", "power_cable"
    subtype: Optional[str] = None         # "potable_water_pipe", "sewer_pipe"
    material: Optional[str] = None        # Linked to material taxonomy
    application: Optional[str] = None     # "water_supply", "drainage"
    modifiers: List[str] = field(default_factory=list)  # ["pressure", "underground"]
    domain: str = "UNKNOWN"               # "CED" or "ETD"


# ── Product Family Hierarchy ──
# Maps base_product → list of valid product families
PRODUCT_FAMILIES: Dict[str, Dict[str, Any]] = {
    # ── CED Products ──
    "pipe": {
        "domain": "CED",
        "families": {
            "pressure_pipe": {
                "applications": ["water_supply", "irrigation", "gas_distribution"],
                "keywords": ["pressure", "potable", "drinking water", "water supply",
                             "irrigation", "gas", "pressure pipe"],
            },
            "non_pressure_pipe": {
                "applications": ["drainage", "sewerage", "soil_waste"],
                "keywords": ["drainage", "sewer", "sewage", "soil", "waste",
                             "non-pressure", "gravity"],
            },
            "casing_pipe": {
                "applications": ["borewell", "tubewell", "casing"],
                "keywords": ["casing", "borewell", "tubewell", "well casing"],
            },
            "conduit_pipe": {
                "applications": ["electrical_conduit", "cable_protection"],
                "keywords": ["conduit", "cable duct", "cable protection"],
            },
        },
        "distinct_from": ["fitting", "valve", "tank", "manhole", "joint"],
    },
    "fitting": {
        "domain": "CED",
        "families": {
            "pipe_fitting": {
                "applications": ["jointing", "connection"],
                "keywords": ["fitting", "joint", "elbow", "tee", "reducer",
                             "coupling", "flange", "bend"],
            },
        },
        "distinct_from": ["pipe", "tube", "tank", "valve"],
    },
    "valve": {
        "domain": "CED",
        "families": {
            "gate_valve": {"keywords": ["gate valve", "sluice valve"]},
            "butterfly_valve": {"keywords": ["butterfly valve"]},
            "check_valve": {"keywords": ["check valve", "non-return valve"]},
            "ball_valve": {"keywords": ["ball valve"]},
        },
        "distinct_from": ["pipe", "tube", "fitting", "tank"],
    },
    "cement": {
        "domain": "CED",
        "families": {
            "portland_cement": {"keywords": ["opc", "portland", "cement"]},
            "pozzolana_cement": {"keywords": ["ppc", "pozzolana", "fly ash"]},
            "slag_cement": {"keywords": ["psc", "slag"]},
        },
        "distinct_from": ["concrete", "aggregate", "sand", "rebar"],
    },
    "rebar": {
        "domain": "CED",
        "families": {
            "tmt_bar": {"keywords": ["tmt", "thermo", "deformed bar"]},
            "plain_bar": {"keywords": ["plain bar", "mild steel bar"]},
        },
        "distinct_from": ["pipe", "tube", "cable", "conductor", "wire"],
    },
    "glass": {
        "domain": "CED",
        "families": {
            "safety_glass": {"keywords": ["safety glass", "tempered", "toughened", "laminated"]},
            "flat_glass": {"keywords": ["float glass", "sheet glass", "flat glass", "plate glass"]},
        },
        "distinct_from": ["panel", "board", "gypsum"],
    },
    "tank": {
        "domain": "CED",
        "families": {
            "water_tank": {"keywords": ["water tank", "overhead tank", "storage tank"]},
            "septic_tank": {"keywords": ["septic tank"]},
        },
        "distinct_from": ["pipe", "tube", "valve"],
    },

    # ── ETD Products ──
    "cable": {
        "domain": "ETD",
        "families": {
            "power_cable": {
                "applications": ["power_distribution", "transmission"],
                "keywords": ["power cable", "xlpe cable", "pvc cable",
                             "armoured cable", "ht cable", "lt cable",
                             "insulated cable", "sheathed cable"],
            },
            "control_cable": {
                "applications": ["control", "instrumentation"],
                "keywords": ["control cable", "instrumentation cable",
                             "pilot cable", "signal cable"],
            },
            "communication_cable": {
                "applications": ["telecommunication", "data"],
                "keywords": ["communication cable", "telephone cable",
                             "optical fibre", "coaxial cable"],
            },
        },
        "distinct_from": ["conductor", "transformer", "switchgear", "meter", "luminaire"],
    },
    "conductor": {
        "domain": "ETD",
        "families": {
            "overhead_conductor": {
                "keywords": ["overhead conductor", "acsr", "aaac", "aac",
                             "bare conductor", "overhead line"],
            },
            "winding_wire": {
                "keywords": ["winding wire", "magnet wire", "enamelled wire"],
            },
        },
        "distinct_from": ["cable", "transformer", "switchgear"],
    },
    "transformer": {
        "domain": "ETD",
        "families": {
            "distribution_transformer": {
                "keywords": ["distribution transformer", "up to 2500 kva",
                             "11 kv", "22 kv", "33 kv"],
            },
            "power_transformer": {
                "keywords": ["power transformer", "autotransformer",
                             "grid transformer", "extra high voltage"],
            },
            "instrument_transformer": {
                "keywords": ["current transformer", "voltage transformer",
                             "instrument transformer", "ct", "pt"],
            },
        },
        "distinct_from": ["cable", "conductor", "switchgear", "meter"],
    },
    "switchgear": {
        "domain": "ETD",
        "families": {
            "circuit_breaker": {
                "keywords": ["circuit breaker", "mccb", "acb", "vcb", "sf6"],
            },
            "switch_disconnector": {
                "keywords": ["switch disconnector", "isolator", "load break switch"],
            },
            "panel_board": {
                "keywords": ["switchboard", "panel board", "distribution board",
                             "mcc", "motor control centre"],
            },
        },
        "distinct_from": ["cable", "conductor", "transformer", "meter"],
    },
    "meter": {
        "domain": "ETD",
        "families": {
            "energy_meter": {
                "keywords": ["energy meter", "watt-hour meter", "kwh meter",
                             "static meter", "smart meter", "prepaid meter"],
            },
            "current_meter": {"keywords": ["ammeter", "current meter"]},
            "voltage_meter": {"keywords": ["voltmeter", "voltage meter"]},
        },
        "distinct_from": ["cable", "conductor", "transformer", "switchgear"],
    },
    "luminaire": {
        "domain": "ETD",
        "families": {
            "led_luminaire": {"keywords": ["led", "led luminaire", "led lamp"]},
            "street_light": {"keywords": ["street light", "street lighting"]},
            "industrial_light": {"keywords": ["industrial luminaire", "floodlight"]},
        },
        "distinct_from": ["ballast", "controlgear", "driver", "cable"],
    },
}

# ── Alias → base_product mapping ──
_PRODUCT_ALIASES: Dict[str, str] = {}
for base_prod, info in PRODUCT_FAMILIES.items():
    _PRODUCT_ALIASES[base_prod] = base_prod
    for fam_name, fam_info in info.get("families", {}).items():
        for kw in fam_info.get("keywords", []):
            _PRODUCT_ALIASES[kw.lower()] = base_prod


def resolve_base_product(text: str) -> Optional[str]:
    """
    Resolve a text string to a base product type.
    Uses keyword matching against the product family hierarchy.
    """
    if not text:
        return None
    text_lower = text.strip().lower()

    # 1. Exact base product match
    if text_lower in PRODUCT_FAMILIES:
        return text_lower

    # 2. Longest keyword match
    best_match = None
    best_len = 0
    for alias, base in _PRODUCT_ALIASES.items():
        if alias in text_lower and len(alias) > best_len:
            best_match = base
            best_len = len(alias)

    return best_match


def build_product_signature(
    raw_product: str,
    material: Optional[str] = None,
    application: Optional[str] = None,
    raw_text: str = "",
) -> ProductSignature:
    """
    Build a structured ProductSignature from raw product string and attributes.
    """
    base = resolve_base_product(raw_product) or resolve_base_product(raw_text) or raw_product.lower()

    family_info = PRODUCT_FAMILIES.get(base, {})
    domain = family_info.get("domain", "UNKNOWN")

    # Determine specific product family from keywords
    product_family = ""
    combined_text = f"{raw_product} {raw_text}".lower()
    for fam_name, fam_data in family_info.get("families", {}).items():
        for kw in fam_data.get("keywords", []):
            if kw.lower() in combined_text:
                product_family = fam_name
                break
        if product_family:
            break

    # Extract modifiers
    modifiers = []
    modifier_keywords = ["pressure", "non-pressure", "underground", "overhead",
                         "indoor", "outdoor", "submersible", "portable"]
    for mod in modifier_keywords:
        if mod in combined_text:
            modifiers.append(mod)

    return ProductSignature(
        base_product=base,
        product_family=product_family,
        material=material,
        application=application,
        modifiers=modifiers,
        domain=domain,
    )


def compare_products(
    query_sig: ProductSignature,
    candidate_sig: ProductSignature,
) -> ProductMatchResult:
    """
    Compare two product signatures at the family level.

    Rules:
    1. Different base_products → check distinct_from list → MISMATCH if listed
    2. Same base_product, different families → RELATED (context-dependent)
    3. Same base_product, same family → MATCH
    4. Generic product alone → insufficient for strong match
    """
    q_base = query_sig.base_product
    c_base = candidate_sig.base_product

    if not q_base or not c_base:
        return ProductMatchResult("UNKNOWN", 0.0, "Cannot determine base product for comparison")

    # 1. Different base products
    if q_base != c_base:
        q_info = PRODUCT_FAMILIES.get(q_base, {})
        c_info = PRODUCT_FAMILIES.get(c_base, {})

        # Check if explicitly distinct
        q_distinct = set(q_info.get("distinct_from", []))
        c_distinct = set(c_info.get("distinct_from", []))

        if c_base in q_distinct or q_base in c_distinct:
            return ProductMatchResult(
                "MISMATCH", 0.95,
                f"Product family mismatch: '{q_base}' and '{c_base}' are explicitly distinct product categories"
            )

        # Different domain cross-check
        q_domain = q_info.get("domain", "UNKNOWN")
        c_domain = c_info.get("domain", "UNKNOWN")
        if q_domain != c_domain and q_domain != "UNKNOWN" and c_domain != "UNKNOWN":
            return ProductMatchResult(
                "MISMATCH", 0.90,
                f"Cross-domain product mismatch: '{q_base}' ({q_domain}) vs '{c_base}' ({c_domain})"
            )

        return ProductMatchResult(
            "MISMATCH", 0.80,
            f"Different product types: '{q_base}' vs '{c_base}'"
        )

    # 2. Same base product
    if query_sig.product_family and candidate_sig.product_family:
        if query_sig.product_family == candidate_sig.product_family:
            return ProductMatchResult(
                "MATCH", 0.95,
                f"Same product family: {query_sig.product_family}"
            )
        else:
            # Same base, different family → RELATED but not direct match
            return ProductMatchResult(
                "RELATED", 0.60,
                f"Same base product '{q_base}' but different families: "
                f"'{query_sig.product_family}' vs '{candidate_sig.product_family}'"
            )

    # 3. Same base product, no specific family differentiation
    return ProductMatchResult(
        "MATCH", 0.75,
        f"Same base product type: {q_base}"
    )


def detect_product_from_title(title: str) -> Optional[ProductSignature]:
    """
    Extract a product signature from a standard's title text.
    Used for candidate standards during applicability evaluation.
    """
    if not title:
        return None

    base = resolve_base_product(title)
    if not base:
        return None

    return build_product_signature(title)
