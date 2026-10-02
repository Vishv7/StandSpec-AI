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
    # Polymers & Plastics
    "high density polyethylene": "High Density Polyethylene (HDPE)",
    "cross-linked polyethylene": "Crosslinked Polyethylene (XLPE)",
    "crosslinked polyethylene": "Crosslinked Polyethylene (XLPE)",
    "unplasticized polyvinyl chloride": "Unplasticized Polyvinyl Chloride (uPVC)",
    "polyvinyl chloride": "Polyvinyl Chloride (PVC)",
    "glass fibre reinforced polymer": "Glass Fibre Reinforced Polymer (GFRP)",
    "hdpe": "High Density Polyethylene (HDPE)",
    "xlpe": "Crosslinked Polyethylene (XLPE)",
    "upvc": "Unplasticized Polyvinyl Chloride (uPVC)",
    "pvc": "Polyvinyl Chloride (PVC)",
    "gfrp": "Glass Fibre Reinforced Polymer (GFRP)",
    "frp": "Glass Fibre Reinforced Polymer (GFRP)",
    "polymer": "Polymer",
    # Hindi / Hinglish / Gujarati Plastics
    "एचडीपीई": "High Density Polyethylene (HDPE)",
    "यूपीवीसी": "Unplasticized Polyvinyl Chloride (uPVC)",
    "पीवीसी": "Polyvinyl Chloride (PVC)",
    "एक्सएलपीई": "Crosslinked Polyethylene (XLPE)",
    "એચડીપીઇ": "High Density Polyethylene (HDPE)",
    "યુપીવીસી": "Unplasticized Polyvinyl Chloride (uPVC)",
    
    # Metals & Steels
    "high strength deformed steel": "High Strength Deformed Steel (TMT)",
    "reinforcement bars": "Steel Reinforcement Bars",
    "reinforcement bar": "Steel Reinforcement Bars",
    "galvanized iron": "Galvanized Iron (GI)",
    "stainless steel": "Stainless Steel",
    "structural steel": "Structural Steel",
    "mild steel": "Mild Steel",
    "ductile iron": "Ductile Iron",
    "cast iron": "Cast Iron",
    "spun iron": "Cast Iron",
    "fe 500": "High Strength Deformed Steel (Fe 500)",
    "fe 415": "High Strength Deformed Steel (Fe 415)",
    "fe 550": "High Strength Deformed Steel (Fe 550)",
    "tmt": "High Strength Deformed Steel (TMT)",
    "rebar": "Steel Reinforcement Bars",
    "steel": "Steel",
    "aluminium": "Aluminium",
    "aluminum": "Aluminium",
    "copper": "Copper",
    "gi": "Galvanized Iron (GI)",
    "di": "Ductile Iron",
    # Hindi / Hinglish / Gujarati Metals
    "तांबा": "Copper",
    "तांबे": "Copper",
    "તાંબુ": "Copper",
    "tamba": "Copper",
    "taanba": "Copper",
    "taambe": "Copper",
    "एल्युमिनियम": "Aluminium",
    "એલ્યુમિનિયમ": "Aluminium",
    "almunium": "Aluminium",
    "aluminiam": "Aluminium",
    "लोहा": "Cast Iron",
    "लोहे": "Cast Iron",
    "लोखंड": "Cast Iron",
    "loha": "Cast Iron",
    "lohe": "Cast Iron",
    "dhalwan loha": "Cast Iron",
    "tmt sariya": "High Strength Deformed Steel (TMT)",
    "sariya": "Steel Reinforcement Bars",
    "lohe ka sariya": "Steel Reinforcement Bars",
    "chhad": "Steel Reinforcement Bars",
    "स्टील": "Steel",

    # Cements & Minerals
    "rapid hardening portland cement": "Rapid Hardening Portland Cement",
    "ordinary portland cement": "Ordinary Portland Cement (OPC)",
    "portland pozzolana cement": "Portland Pozzolana Cement (PPC)",
    "portland slag cement": "Portland Slag Cement (PSC)",
    "high alumina cement": "High Alumina Cement",
    "opc": "Ordinary Portland Cement (OPC)",
    "ppc": "Portland Pozzolana Cement (PPC)",
    "psc": "Portland Slag Cement (PSC)",
    "float glass": "Float Glass",
    "safety glass": "Safety Glass",
    "glass": "Glass",
    "gypsum plaster board": "Gypsum Plaster Boards",
    "gypsum board": "Gypsum Plaster Boards",
    "gypsum": "Gypsum",
    # Hindi / Hinglish / Gujarati Minerals
    "सीमेंट": "Cement",
    "સિમેન્ટ": "Cement",
    "कंक्रीट": "Concrete",
    "કાચ": "Glass",
    "कांच": "Glass",
    "काँच": "Glass",
    "kaanch": "Glass",
    "kach": "Glass",
    "ret": "Fine Aggregate",
    "rodi": "Coarse Aggregate",
    "bajri": "Coarse Aggregate",
}

# ── Multilingual Application Synonyms ──

APPLICATION_SYNONYMS = {
    # Potable water (English, Hindi, Gujarati, Hinglish)
    "drinking water": "Potable Water Supply",
    "potable water": "Potable Water Supply",
    "potable water supplies": "Potable Water Supply",
    "potable": "Potable Water Supply",
    "water distribution": "Potable Water Supply",
    "water supply": "Potable Water Supply",
    "peene ka paani": "Potable Water Supply",
    "peene ke paani": "Potable Water Supply",
    "peene ke pani": "Potable Water Supply",
    "paani ka pipe": "Potable Water Supply",
    "paani pipe": "Potable Water Supply",
    "pani ka pipe": "Potable Water Supply",
    "paani supply": "Potable Water Supply",
    "nal ka pipe": "Potable Water Supply",
    "paani": "Potable Water Supply",
    "pani": "Potable Water Supply",
    "पीने का पानी": "Potable Water Supply",
    "पीने के पानी": "Potable Water Supply",
    "पेयजल आपूर्ति": "Potable Water Supply",
    "पेयजल": "Potable Water Supply",
    "પાણી પુરવઠો": "Potable Water Supply",
    "પીવાનું પાણી": "Potable Water Supply",
    "પીવાના પાણી": "Potable Water Supply",
    
    # Sewerage & Drainage
    "industrial waste": "Sewerage and Industrial Waste",
    "sewerage": "Sewerage and Drainage",
    "drainage": "Sewerage and Drainage",
    "waste disposal": "Sewerage and Drainage",
    "ganda paani": "Sewerage and Drainage",
    "naali": "Sewerage and Drainage",
    "सीवरेज": "Sewerage and Drainage",
    "ड्रेनेज": "Sewerage and Drainage",
    
    # Tubewell Casing / Screen
    "casing and screen": "Borewell / Tubewell Casing",
    "screen and casing": "Borewell / Tubewell Casing",
    "tubewell casing": "Borewell / Tubewell Casing",
    "borewell casing": "Borewell / Tubewell Casing",
    "tubewell": "Borewell / Tubewell Casing",
    "borewell": "Borewell / Tubewell Casing",
    "tube-well": "Borewell / Tubewell Casing",
    
    # Power Transmission & Distribution
    "bulk transmission": "High Voltage Power Transmission",
    "grid substation": "High Voltage Power Transmission",
    "power distribution": "Power Distribution",
    "distribution network": "Power Distribution",
    "rural electrification": "Power Distribution",
    "substation": "Substation Equipment",
    "substation ke liye": "High Voltage Power Transmission",
    "bijli ka taar": "Power Distribution",
    "bijli taar": "Power Distribution",
    "bijli vitran": "Power Distribution",
    "bijli supply": "Power Distribution",
    "bijli": "Power Distribution",
    "बिजली वितरण": "Power Distribution",
    "વીજળી વિતરણ": "Power Distribution",
}

# ── Linguistic and Multilingual Patterns ──

DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')
GUJARATI_RE = re.compile(r'[\u0A80-\u0AFF]')

HINGLISH_KEYWORDS = {
    "chahiye", "khareedna", "kharidari", "mangwana", "lagana", "lagane", "ke liye",
    "wala", "wali", "wale", "bijli", "bijlee", "taar", "taare", "taaren", "paani",
    "pani", "peene", "darwaja", "darwaza", "khidki", "sarkari", "kaam", "hona",
    "hoti", "karna", "pipe", "paip", "sariya", "loha", "lohe", "tamba", "taanba",
    "almunium", "ret", "rodi", "bajri", "mitti", "chhat", "kaanch", "kach",
    "batti", "bulub", "pankha"
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


def normalize_diameter(text: str) -> Optional[str]:
    """
    Normalize pipe or bar diameter / nominal bore (e.g. '110 mm', 'DN 110', '110 मिमी').
    Preserves units and maps to canonical DN representation.
    """
    m = re.search(
        r'\b(?:dn\s*[:\-]?\s*(\d+(?:\.\d+)?)|(?:diameter|od|nb)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:mm)?|(\d+(?:\.\d+)?)\s*mm\s*(?:diameter|od|nb|dn)?|(\d+(?:\.\d+)?)\s*(?:मिमी|મીમી))\b',
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    val = m.group(1) or m.group(2) or m.group(3) or m.group(4)
    if not val:
        return None
    val_clean = int(float(val)) if float(val).is_integer() else float(val)
    return f"DN {val_clean} mm"


def normalize_pressure(text: str) -> Optional[str]:
    """
    Normalize pressure ratings (e.g. 'PN 10', '1.0 MPa', '10 bar', 'Class 3').
    """
    m = re.search(r'\b(?:pn\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:bar|mpa|kg/cm2)|class\s*(\d+))\b', text, re.IGNORECASE)
    if not m:
        return None
    if m.group(1):
        return f"PN {m.group(1)}"
    elif m.group(2):
        return f"{m.group(2)} MPa"
    elif m.group(3):
        return f"Class {m.group(3)}"
    return None


def normalize_application(text: str) -> Optional[str]:
    """
    Normalize application intent across English, Hindi, Hinglish, and Gujarati.
    """
    cleaned = text.lower().strip()
    sorted_apps = sorted(APPLICATION_SYNONYMS.items(), key=lambda x: len(x[0]), reverse=True)
    for syn, canonical in sorted_apps:
        if syn in cleaned:
            return canonical
    return None


def normalize_temperature(text: str) -> Optional[str]:
    """Normalize temperature specification to °C."""
    m = TEMPERATURE_RE.search(text)
    if not m:
        return None
    val = m.group(1)
    return f"{val} °C"


def normalize_material(text: str) -> Optional[str]:
    """
    Normalize material descriptions to canonical terms using longest-first matching.
    Guarantees compound phrases match before single-word constituents.
    """
    cleaned = text.lower().strip()
    sorted_synonyms = sorted(MATERIAL_SYNONYMS.items(), key=lambda x: len(x[0]), reverse=True)
    for syn, canonical in sorted_synonyms:
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
