"""
Technical Attribute and Linguistic Normalizer — StandSpec AI (Phase 6)
Normalizes technical specifications (voltage, dimensions, materials, grades)
and detects procurement language (English, Hindi, Gujarati, Hinglish).
"""

import re
from typing import Optional


# ── Technical Unit Normalizations ──

VOLTAGE_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(k?v)\b', re.IGNORECASE)
FREQUENCY_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(k?hz)\b', re.IGNORECASE)
DIMENSION_RE = re.compile(r'(\d+(?:\s*[xX*]\s*\d+)?)\s*(?:sq\.?\s*mm|sqmm|mm2|mm²)\b', re.IGNORECASE)
TEMPERATURE_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(?:°\s*C|deg(?:rees?)?\s*C|celsius)\b', re.IGNORECASE)

MATERIAL_SYNONYMS = {
    "xlpe": "Crosslinked Polyethylene (XLPE)",
    "cross-linked polyethylene": "Crosslinked Polyethylene (XLPE)",
    "crosslinked polyethylene": "Crosslinked Polyethylene (XLPE)",
    "pvc": "Polyvinyl Chloride (PVC)",
    "polyvinyl chloride": "Polyvinyl Chloride (PVC)",
    "upvc": "Unplasticized Polyvinyl Chloride (uPVC)",
    "aluminium": "Aluminium",
    "aluminum": "Aluminium",
    "copper": "Copper",
    "gi": "Galvanized Iron (GI)",
    "galvanized iron": "Galvanized Iron (GI)",
    "stainless steel": "Stainless Steel",
    "mild steel": "Mild Steel",
    "structural steel": "Structural Steel",
    "steel": "Steel",
    "tmt": "High Strength Deformed Steel (TMT)",
    "fe 500": "High Strength Deformed Steel (Fe 500)",
    "fe 415": "High Strength Deformed Steel (Fe 415)",
    "ductile iron": "Ductile Iron",
    "di": "Ductile Iron",
    "cast iron": "Cast Iron",
    "spun iron": "Cast Iron",
    "gfrp": "Glass Fibre Reinforced Polymer (GFRP)",
    "polymer": "Polymer",
    "glass": "Glass",
    "float glass": "Float Glass",
    "gypsum": "Gypsum",
    "opc": "Ordinary Portland Cement (OPC)",
    "ppc": "Portland Pozzolana Cement (PPC)",
    "psc": "Portland Slag Cement (PSC)",
}

# ── Linguistic and Multilingual Patterns ──

DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')
GUJARATI_RE = re.compile(r'[\u0A80-\u0AFF]')

HINGLISH_KEYWORDS = {
    "chahiye", "lagana", "lagane", "ke liye", "wala", "wali", "wale",
    "bijli", "taar", "paani", "darwaja", "khidki", "sarkari",
    "kaam", "hona", "hoti", "karna"
}



def normalize_voltage(text: str) -> Optional[str]:
    """Normalize voltage text to standard numeric volt string with unit (e.g. '11 kV' -> '11000 V')."""
    m = VOLTAGE_RE.search(text)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "kv":
        volts = int(val * 1000)
    else:
        volts = int(val)
    return f"{volts} V"


def normalize_frequency(text: str) -> Optional[str]:
    """Normalize frequency text to standard Hz representation (e.g. '50 Hz')."""
    m = FREQUENCY_RE.search(text)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "khz":
        hz = int(val * 1000)
    else:
        hz = int(val)
    return f"{hz} Hz"


def normalize_dimensions(text: str) -> Optional[str]:
    """Normalize cable or conductor dimensions to mm² (e.g. '3 x 300 sq.mm' -> '3x300 mm²')."""
    m = DIMENSION_RE.search(text)
    if not m:
        return None
    spec = m.group(1).replace(" ", "").lower()
    return f"{spec} mm²"


def normalize_temperature(text: str) -> Optional[str]:
    """Normalize temperature specification to °C."""
    m = TEMPERATURE_RE.search(text)
    if not m:
        return None
    val = m.group(1)
    return f"{val} °C"


def normalize_material(text: str) -> Optional[str]:
    """Normalize material descriptions to canonical terms."""
    cleaned = text.lower().strip()
    for syn, canonical in MATERIAL_SYNONYMS.items():
        if syn in cleaned:
            return canonical
    return None


def detect_language(text: str) -> dict:
    """
    Detect the procurement text language: English, Hindi, Gujarati, or Hinglish.
    Returns language_detection metadata dictionary.
    """
    has_devanagari = bool(DEVANAGARI_RE.search(text))
    has_gujarati = bool(GUJARATI_RE.search(text))

    words = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
    hinglish_matches = words.intersection(HINGLISH_KEYWORDS)
    has_hinglish = len(hinglish_matches) >= 1

    if has_gujarati:
        detected = "gu"
        confidence = 0.95
    elif has_devanagari:
        detected = "hi"
        confidence = 0.95
    elif has_hinglish:
        detected = "hinglish"
        confidence = 0.85
    else:
        detected = "en"
        confidence = 0.98

    return {
        "detected": detected,
        "confidence": confidence,
        "contains_hinglish": has_hinglish,
        "contains_hindi": has_devanagari,
        "contains_gujarati": has_gujarati,
    }
