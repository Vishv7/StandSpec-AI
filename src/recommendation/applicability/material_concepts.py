"""
Material Concept Taxonomy and Compatibility Layer — StandSpec AI (Phase 4, Checkpoint 2)
PS 26108 §7: Canonical material taxonomy with concept-level compatibility.

Replaces substring/stem-based material matching with structured canonical concepts.
Each material concept has:
  - family: top-level material family (POLYMER, FERROUS_METAL, etc.)
  - base: canonical base material (POLYETHYLENE, IRON, etc.)
  - canonical_name: unique canonical identifier
  - aliases: all known synonyms, abbreviations, trade names

Contradiction pairs define materials that are fundamentally incompatible.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Set
import re


class MaterialFamily(str, Enum):
    """Top-level material classification families."""
    POLYMER = "POLYMER"
    FERROUS_METAL = "FERROUS_METAL"
    NON_FERROUS_METAL = "NON_FERROUS_METAL"
    CEMENTITIOUS = "CEMENTITIOUS"
    CERAMIC = "CERAMIC"
    COMPOSITE = "COMPOSITE"
    GLASS = "GLASS"
    INSULATION = "INSULATION"
    WOOD = "WOOD"
    UNKNOWN = "UNKNOWN"


class MaterialMatchResult(str, Enum):
    """Result of material compatibility check."""
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"
    SAME_FAMILY = "SAME_FAMILY"
    RELATED = "RELATED"


# ── Canonical Material Taxonomy ──
# Each entry: canonical_name → {family, base, aliases}

MATERIAL_TAXONOMY: Dict[str, Dict[str, Any]] = {
    # ── Polymers ──
    "HDPE": {
        "family": MaterialFamily.POLYMER,
        "base": "POLYETHYLENE",
        "aliases": ["hdpe", "pe-hd", "pe 100", "pe 80", "pe100", "pe80",
                     "high density polyethylene", "high-density polyethylene",
                     "polyethylene", "एचडीपीई", "पॉलीथीन"],
    },
    "LDPE": {
        "family": MaterialFamily.POLYMER,
        "base": "POLYETHYLENE",
        "aliases": ["ldpe", "pe-ld", "low density polyethylene", "low-density polyethylene"],
    },
    "PVC": {
        "family": MaterialFamily.POLYMER,
        "base": "POLYVINYL_CHLORIDE",
        "aliases": ["pvc", "polyvinyl chloride", "poly vinyl chloride", "पीवीसी"],
    },
    "UPVC": {
        "family": MaterialFamily.POLYMER,
        "base": "POLYVINYL_CHLORIDE",
        "aliases": ["upvc", "u-pvc", "pvc-u", "unplasticized pvc",
                     "unplasticized polyvinyl chloride", "rigid pvc", "यूपीवीसी"],
    },
    "CPVC": {
        "family": MaterialFamily.POLYMER,
        "base": "POLYVINYL_CHLORIDE",
        "aliases": ["cpvc", "chlorinated pvc", "chlorinated polyvinyl chloride"],
    },
    "XLPE": {
        "family": MaterialFamily.POLYMER,
        "base": "CROSSLINKED_POLYETHYLENE",
        "aliases": ["xlpe", "cross linked polyethylene", "crosslinked polyethylene",
                     "cross-linked polyethylene", "xple"],
    },
    "PP": {
        "family": MaterialFamily.POLYMER,
        "base": "POLYPROPYLENE",
        "aliases": ["pp", "polypropylene", "poly propylene"],
    },
    "GRP": {
        "family": MaterialFamily.COMPOSITE,
        "base": "GLASS_REINFORCED_POLYMER",
        "aliases": ["grp", "frp", "glass reinforced plastic", "fibre reinforced plastic",
                     "fiber reinforced plastic", "glass fibre reinforced"],
    },
    "RUBBER": {
        "family": MaterialFamily.POLYMER,
        "base": "RUBBER",
        "aliases": ["rubber", "epdm", "nbr", "nitrile", "neoprene", "natural rubber",
                     "synthetic rubber", "silicone rubber"],
    },

    # ── Ferrous Metals ──
    "CAST_IRON": {
        "family": MaterialFamily.FERROUS_METAL,
        "base": "IRON",
        "aliases": ["cast iron", "ci", "grey iron", "gray iron",
                     "centrifugally cast iron", "spun iron", "कास्ट आयरन"],
    },
    "DUCTILE_IRON": {
        "family": MaterialFamily.FERROUS_METAL,
        "base": "DUCTILE_IRON",
        "aliases": ["ductile iron", "di", "sg iron", "spheroidal graphite iron",
                     "nodular iron", "di pipe", "डक्टाइल आयरन"],
    },
    "MILD_STEEL": {
        "family": MaterialFamily.FERROUS_METAL,
        "base": "STEEL",
        "aliases": ["mild steel", "ms", "carbon steel", "low carbon steel",
                     "structural steel", "माइल्ड स्टील"],
    },
    "STAINLESS_STEEL": {
        "family": MaterialFamily.FERROUS_METAL,
        "base": "STEEL",
        "aliases": ["stainless steel", "ss", "ss304", "ss316", "austenitic steel",
                     "corrosion resistant steel", "स्टेनलेस स्टील"],
    },
    "TMT_STEEL": {
        "family": MaterialFamily.FERROUS_METAL,
        "base": "STEEL",
        "aliases": ["tmt", "tmt steel", "tmt bar", "tmt rebar", "thermo mechanically treated",
                     "deformed bar", "reinforcement bar", "rebar",
                     "fe 500", "fe 500d", "fe 550", "fe 550d", "fe 415"],
    },
    "GALVANIZED_STEEL": {
        "family": MaterialFamily.FERROUS_METAL,
        "base": "STEEL",
        "aliases": ["galvanized steel", "gi", "galvanised steel", "gi pipe",
                     "hot dip galvanized", "hdg", "जीआई"],
    },

    # ── Non-Ferrous Metals ──
    "COPPER": {
        "family": MaterialFamily.NON_FERROUS_METAL,
        "base": "COPPER",
        "aliases": ["copper", "cu", "electrolytic copper", "ofc",
                     "oxygen free copper", "copper conductor", "तांबा"],
    },
    "ALUMINIUM": {
        "family": MaterialFamily.NON_FERROUS_METAL,
        "base": "ALUMINIUM",
        "aliases": ["aluminium", "aluminum", "al", "alloy aluminium",
                     "aluminium conductor", "aac", "aaac", "acsr", "एल्युमिनियम"],
    },
    "BRASS": {
        "family": MaterialFamily.NON_FERROUS_METAL,
        "base": "COPPER_ALLOY",
        "aliases": ["brass", "gun metal", "gunmetal", "bronze", "phosphor bronze"],
    },
    "LEAD": {
        "family": MaterialFamily.NON_FERROUS_METAL,
        "base": "LEAD",
        "aliases": ["lead", "pb", "lead sheathed"],
    },

    # ── Cementitious ──
    "OPC": {
        "family": MaterialFamily.CEMENTITIOUS,
        "base": "PORTLAND_CEMENT",
        "aliases": ["opc", "ordinary portland cement", "portland cement", "cement",
                     "grade 33", "grade 43", "grade 53", "सीमेंट"],
    },
    "PPC": {
        "family": MaterialFamily.CEMENTITIOUS,
        "base": "PORTLAND_CEMENT",
        "aliases": ["ppc", "portland pozzolana cement", "pozzolana cement",
                     "fly ash cement"],
    },
    "PSC": {
        "family": MaterialFamily.CEMENTITIOUS,
        "base": "PORTLAND_CEMENT",
        "aliases": ["psc", "portland slag cement", "slag cement", "blast furnace slag cement"],
    },
    "CONCRETE": {
        "family": MaterialFamily.CEMENTITIOUS,
        "base": "CONCRETE",
        "aliases": ["concrete", "rcc", "reinforced concrete", "ready mix concrete",
                     "rmc", "m20", "m25", "m30", "m40", "कंक्रीट"],
    },

    # ── Insulation Materials ──
    "PAPER_INSULATION": {
        "family": MaterialFamily.INSULATION,
        "base": "PAPER",
        "aliases": ["paper insulated", "paper covered", "oil impregnated paper",
                     "kraft paper", "impregnated paper"],
    },
    "ENAMEL_INSULATION": {
        "family": MaterialFamily.INSULATION,
        "base": "ENAMEL",
        "aliases": ["enamelled", "enamel insulated", "enamel covered",
                     "polyester enamel", "polyurethane enamel"],
    },

    # ── Glass ──
    "FLOAT_GLASS": {
        "family": MaterialFamily.GLASS,
        "base": "GLASS",
        "aliases": ["float glass", "sheet glass", "flat glass", "plate glass",
                     "window glass", "clear glass"],
    },
    "TEMPERED_GLASS": {
        "family": MaterialFamily.GLASS,
        "base": "GLASS",
        "aliases": ["tempered glass", "toughened glass", "safety glass",
                     "heat strengthened glass"],
    },
}


# ── Material Contradiction Pairs ──
# Pairs of material families or canonical names that are fundamentally incompatible.
# Symmetric: (A, B) implies (B, A).

MATERIAL_FAMILY_CONTRADICTIONS: Set[tuple] = {
    # Cross-family contradictions
    (MaterialFamily.POLYMER, MaterialFamily.FERROUS_METAL),
    (MaterialFamily.POLYMER, MaterialFamily.NON_FERROUS_METAL),
    (MaterialFamily.POLYMER, MaterialFamily.CEMENTITIOUS),
    (MaterialFamily.FERROUS_METAL, MaterialFamily.CEMENTITIOUS),
    (MaterialFamily.FERROUS_METAL, MaterialFamily.NON_FERROUS_METAL),
    (MaterialFamily.NON_FERROUS_METAL, MaterialFamily.CEMENTITIOUS),
    (MaterialFamily.GLASS, MaterialFamily.POLYMER),
    (MaterialFamily.GLASS, MaterialFamily.FERROUS_METAL),
}

# Specific canonical material contradictions (within or across families)
MATERIAL_CANONICAL_CONTRADICTIONS: Set[tuple] = {
    ("XLPE", "PAPER_INSULATION"),       # Cable insulation types
    ("XLPE", "ENAMEL_INSULATION"),      # Cable insulation types
    ("PVC", "PAPER_INSULATION"),        # Cable insulation types
    ("ALUMINIUM", "COPPER"),            # Conductor materials
    ("COPPER", "ALUMINIUM"),            # Conductor materials
    ("CAST_IRON", "DUCTILE_IRON"),      # Distinct iron types (related but different standards)
    ("HDPE", "UPVC"),                   # Different polymer pipe materials
    ("HDPE", "CPVC"),                   # Different polymer pipe materials
    ("PVC", "HDPE"),                    # Different polymer pipe materials
    ("OPC", "PPC"),                     # Different cement types (within same family but distinct)
    ("OPC", "PSC"),                     # Different cement types
}

# Materials that are compatible (same material in different naming)
MATERIAL_EQUIVALENCES: Dict[str, Set[str]] = {
    "PVC": {"UPVC", "CPVC"},           # PVC is a broader category
    "UPVC": {"PVC"},                   # UPVC is a form of PVC
    "HDPE": {"LDPE"},                  # Both polyethylene (though different densities)
}


def _build_alias_index() -> Dict[str, str]:
    """Build a lowercase alias → canonical_name lookup index."""
    index: Dict[str, str] = {}
    for canonical, info in MATERIAL_TAXONOMY.items():
        index[canonical.lower()] = canonical
        for alias in info.get("aliases", []):
            index[alias.lower()] = canonical
    return index


_ALIAS_INDEX = _build_alias_index()


def resolve_material(raw_material: str) -> Optional[str]:
    """
    Resolve a raw material string to its canonical name.
    Uses alias index with progressive matching (exact → contains → token).
    Returns None if no match found.
    """
    if not raw_material:
        return None
    raw_lower = raw_material.strip().lower()

    # 1. Exact alias match
    if raw_lower in _ALIAS_INDEX:
        return _ALIAS_INDEX[raw_lower]

    # 2. Check if any alias is contained in the raw material
    best_match = None
    best_len = 0
    for alias, canonical in _ALIAS_INDEX.items():
        if alias in raw_lower and len(alias) > best_len:
            best_match = canonical
            best_len = len(alias)
    if best_match and best_len >= 2:
        return best_match

    return None


def get_material_family(canonical_name: str) -> MaterialFamily:
    """Get the material family for a canonical material name."""
    info = MATERIAL_TAXONOMY.get(canonical_name)
    if info:
        return info["family"]
    return MaterialFamily.UNKNOWN


def resolve_material_compatibility(
    query_material: str,
    candidate_material: str,
) -> Tuple[MaterialMatchResult, str]:
    """
    Determine compatibility between query material and candidate material
    at the concept level.

    Returns:
        (result, reason) tuple where result is MATCH, MISMATCH, UNKNOWN, etc.
    """
    q_canonical = resolve_material(query_material)
    c_canonical = resolve_material(candidate_material)

    if not q_canonical and not c_canonical:
        return MaterialMatchResult.UNKNOWN, "Neither material could be resolved to a canonical concept"
    if not q_canonical:
        return MaterialMatchResult.UNKNOWN, f"Query material '{query_material}' could not be resolved"
    if not c_canonical:
        return MaterialMatchResult.UNKNOWN, f"Candidate material '{candidate_material}' could not be resolved"

    # 1. Exact canonical match
    if q_canonical == c_canonical:
        return MaterialMatchResult.MATCH, f"Exact material match: {q_canonical}"

    # 2. Check equivalences
    q_equivs = MATERIAL_EQUIVALENCES.get(q_canonical, set())
    c_equivs = MATERIAL_EQUIVALENCES.get(c_canonical, set())
    if c_canonical in q_equivs or q_canonical in c_equivs:
        return MaterialMatchResult.MATCH, f"Equivalent materials: {q_canonical} ↔ {c_canonical}"

    # 3. Check canonical contradictions (symmetric)
    if (q_canonical, c_canonical) in MATERIAL_CANONICAL_CONTRADICTIONS or \
       (c_canonical, q_canonical) in MATERIAL_CANONICAL_CONTRADICTIONS:
        return MaterialMatchResult.MISMATCH, \
            f"Material contradiction: {q_canonical} vs {c_canonical} are incompatible material types"

    # 4. Check family-level contradictions
    q_family = get_material_family(q_canonical)
    c_family = get_material_family(c_canonical)

    if q_family != MaterialFamily.UNKNOWN and c_family != MaterialFamily.UNKNOWN:
        if (q_family, c_family) in MATERIAL_FAMILY_CONTRADICTIONS or \
           (c_family, q_family) in MATERIAL_FAMILY_CONTRADICTIONS:
            return MaterialMatchResult.MISMATCH, \
                f"Material family contradiction: {q_canonical} ({q_family.value}) vs {c_canonical} ({c_family.value})"

    # 5. Same family, same base → related match
    q_info = MATERIAL_TAXONOMY.get(q_canonical, {})
    c_info = MATERIAL_TAXONOMY.get(c_canonical, {})
    if q_info.get("base") and q_info.get("base") == c_info.get("base"):
        return MaterialMatchResult.SAME_FAMILY, \
            f"Same material base ({q_info['base']}): {q_canonical} vs {c_canonical}"

    # 6. Same family, different base → related
    if q_family == c_family and q_family != MaterialFamily.UNKNOWN:
        return MaterialMatchResult.RELATED, \
            f"Same family ({q_family.value}): {q_canonical} vs {c_canonical}"

    # 7. Different families, no explicit contradiction → unknown
    return MaterialMatchResult.UNKNOWN, \
        f"No explicit compatibility data: {q_canonical} ({q_family.value}) vs {c_canonical} ({c_family.value})"


def extract_material_from_text(text: str) -> Optional[str]:
    """
    Extract and resolve material from a title/scope text string.
    Used to identify candidate standard's primary material from its metadata.
    """
    if not text:
        return None
    text_lower = text.lower()

    # Try longest alias first for best precision
    candidates = []
    for alias, canonical in _ALIAS_INDEX.items():
        if len(alias) >= 2 and alias in text_lower:
            candidates.append((len(alias), canonical, alias))

    if candidates:
        candidates.sort(reverse=True)  # Longest match first
        return candidates[0][1]  # canonical name

    return None
