"""
Multilingual Query Normalizer — StandSpec AI (Phase 12, Checkpoint 5)
PS 26108 §13: Hardened multilingual normalization pipeline.

Provides a unified normalization pipeline for procurement queries across:
  - English (standard BIS procurement language)
  - Hindi (Devanagari script)
  - Gujarati (Gujarati script)
  - Hinglish (romanized Hindi mixed with English)
  - Tamil (Tamil script, stub coverage)

Key principles:
  1. Normalize to English canonical forms BEFORE retrieval
  2. Preserve original text for provenance
  3. Track transliteration confidence
  4. Never lose information — augment, don't replace
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field


# ── Transliteration Maps ──
# Romanized Hindi/Hinglish → English canonical forms for procurement terms

TRANSLITERATION_MAP: Dict[str, str] = {
    # Products (Hinglish → English)
    "pipe": "pipe",
    "paip": "pipe",
    "nali": "pipe",
    "naali": "drain pipe",
    "cable": "cable",
    "taar": "cable",
    "taare": "cables",
    "tar": "cable",
    "bijli ka taar": "power cable",
    "bijli taar": "power cable",
    "sariya": "reinforcement bar",
    "tmt sariya": "TMT reinforcement bar",
    "lohe ka sariya": "steel reinforcement bar",
    "chhad": "reinforcement bar",
    "meter": "meter",
    "bijli meter": "energy meter",
    "bijli ka meter": "energy meter",
    "transformer": "transformer",
    "valve": "valve",
    "switch": "switch",
    "pankha": "fan",
    "batti": "light",
    "bulub": "light bulb",
    "bulb": "light bulb",
    "darwaja": "door",
    "darwaza": "door",
    "khidki": "window",
    "chhat": "roof",

    # Materials (Hinglish → English)
    "loha": "iron",
    "lohe": "iron",
    "dhalwan loha": "cast iron",
    "tamba": "copper",
    "taanba": "copper",
    "taambe": "copper",
    "almunium": "aluminium",
    "aluminiam": "aluminium",
    "cement": "cement",
    "ret": "fine aggregate",
    "rodi": "coarse aggregate",
    "bajri": "coarse aggregate",
    "mitti": "soil",
    "kaanch": "glass",
    "kach": "glass",
    "steel": "steel",
    "ispaat": "steel",

    # Applications (Hinglish → English)
    "paani": "water",
    "pani": "water",
    "peene ka paani": "potable water",
    "peene ke paani": "potable water",
    "peene ke pani": "potable water",
    "paani supply": "water supply",
    "nal ka pipe": "water supply pipe",
    "ganda paani": "sewage water",
    "bijli": "electricity",
    "bijli supply": "power supply",
    "bijli vitran": "power distribution",
    "substation ke liye": "for substation",
    "sarkari kaam": "government work",
    "khareedna": "procurement",
    "kharidari": "procurement",
    "mangwana": "procurement",

    # Actions / Modifiers
    "chahiye": "required",
    "lagana": "install",
    "lagane": "installation",
    "ke liye": "for",
    "wala": "type",
    "wali": "type",
    "wale": "type",
    "hona chahiye": "should be",
    "karna": "to do",
}

# ── Devanagari (Hindi) → English Product/Material Mappings ──

DEVANAGARI_MAP: Dict[str, str] = {
    # Products
    "पाइप": "pipe",
    "केबल": "cable",
    "तार": "cable",
    "बिजली": "electricity",
    "बिजली वितरण": "power distribution",
    "ट्रांसफार्मर": "transformer",
    "मीटर": "meter",
    "वाल्व": "valve",
    "स्विच": "switch",
    "पंखा": "fan",
    "बल्ब": "light bulb",
    "दरवाजा": "door",
    "खिड़की": "window",

    # Materials
    "तांबा": "copper",
    "तांबे": "copper",
    "एल्युमिनियम": "aluminium",
    "लोहा": "iron",
    "लोहे": "iron",
    "लोखंड": "iron",
    "इस्पात": "steel",
    "स्टील": "steel",
    "सीमेंट": "cement",
    "कंक्रीट": "concrete",
    "कांच": "glass",
    "काँच": "glass",

    # Specific abbreviation transliterations
    "एचडीपीई": "HDPE",
    "यूपीवीसी": "uPVC",
    "पीवीसी": "PVC",
    "एक्सएलपीई": "XLPE",

    # Applications
    "पीने का पानी": "potable water",
    "पीने के पानी": "potable water",
    "पेयजल आपूर्ति": "potable water supply",
    "पेयजल": "potable water",
    "जल आपूर्ति": "water supply",
    "सीवरेज": "sewerage",
    "ड्रेनेज": "drainage",
    "मिमी": "mm",
}

# ── Gujarati → English Product/Material Mappings ──

GUJARATI_MAP: Dict[str, str] = {
    # Materials
    "તાંબુ": "copper",
    "એલ્યુમિનિયમ": "aluminium",
    "સિમેન્ટ": "cement",
    "કાચ": "glass",
    "એચડીપીઇ": "HDPE",
    "યુપીવીસી": "uPVC",

    # Applications
    "પાણી પુરવઠો": "water supply",
    "પીવાનું પાણી": "potable water",
    "પીવાના પાણી": "potable water",
    "વીજળી વિતરણ": "power distribution",

    # Units
    "મીમી": "mm",
}


@dataclass
class NormalizationResult:
    """
    Result of multilingual query normalization.
    Preserves original text while providing normalized English form.
    """
    original_text: str
    normalized_text: str
    detected_language: str
    language_confidence: float
    transliterations_applied: List[Dict[str, str]] = field(default_factory=list)
    technical_terms_resolved: List[Dict[str, str]] = field(default_factory=list)
    is_multilingual: bool = False
    normalization_confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "detected_language": self.detected_language,
            "language_confidence": self.language_confidence,
            "transliterations_applied": self.transliterations_applied,
            "technical_terms_resolved": self.technical_terms_resolved,
            "is_multilingual": self.is_multilingual,
            "normalization_confidence": self.normalization_confidence,
        }


# ── Script Detection Patterns ──
DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')
GUJARATI_RE = re.compile(r'[\u0A80-\u0AFF]')
TAMIL_RE = re.compile(r'[\u0B80-\u0BFF]')
BENGALI_RE = re.compile(r'[\u0980-\u09FF]')

HINGLISH_KEYWORDS = {
    "chahiye", "khareedna", "kharidari", "mangwana", "lagana", "lagane", "ke liye",
    "wala", "wali", "wale", "bijli", "bijlee", "taar", "taare", "taaren", "paani",
    "pani", "peene", "darwaja", "darwaza", "khidki", "sarkari", "kaam", "hona",
    "hoti", "karna", "pipe", "paip", "sariya", "loha", "lohe", "tamba", "taanba",
    "almunium", "ret", "rodi", "bajri", "mitti", "chhat", "kaanch", "kach",
    "batti", "bulub", "pankha", "meter", "cable", "valve", "bijli",
    "substation", "vitran", "ispaat",
}


def detect_language(text: str) -> Dict[str, Any]:
    """
    Detect the procurement text language with enhanced coverage.
    Returns structured language detection metadata.
    """
    has_devanagari = bool(DEVANAGARI_RE.search(text))
    has_gujarati = bool(GUJARATI_RE.search(text))
    has_tamil = bool(TAMIL_RE.search(text))
    has_bengali = bool(BENGALI_RE.search(text))

    words = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
    hinglish_matches = words.intersection(HINGLISH_KEYWORDS)
    has_hinglish = len(hinglish_matches) >= 2  # Require at least 2 keywords for Hinglish

    if has_gujarati:
        detected = "gu"
        confidence = 0.95
    elif has_devanagari:
        detected = "hi"
        confidence = 0.95
    elif has_tamil:
        detected = "ta"
        confidence = 0.90
    elif has_bengali:
        detected = "bn"
        confidence = 0.90
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
        "contains_tamil": has_tamil,
        "contains_bengali": has_bengali,
        "is_multilingual": has_devanagari or has_gujarati or has_hinglish or has_tamil or has_bengali,
        "hinglish_keywords_found": list(hinglish_matches) if has_hinglish else [],
    }


def transliterate_to_english(text: str, lang_meta: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    """
    Transliterate non-English text to English canonical forms.
    Returns (normalized_text, list of transliteration records).
    """
    result = text
    records = []
    detected = lang_meta.get("detected", "en")

    if detected == "en" and not lang_meta.get("is_multilingual", False):
        return result, records

    # Apply Devanagari mappings (longest first)
    if lang_meta.get("contains_hindi", False):
        sorted_deva = sorted(DEVANAGARI_MAP.items(), key=lambda x: len(x[0]), reverse=True)
        for src, tgt in sorted_deva:
            if src in result:
                result = result.replace(src, tgt)
                records.append({"source": src, "target": tgt, "script": "devanagari"})

    # Apply Gujarati mappings (longest first)
    if lang_meta.get("contains_gujarati", False):
        sorted_guj = sorted(GUJARATI_MAP.items(), key=lambda x: len(x[0]), reverse=True)
        for src, tgt in sorted_guj:
            if src in result:
                result = result.replace(src, tgt)
                records.append({"source": src, "target": tgt, "script": "gujarati"})

    # Apply Hinglish transliteration (longest first, case-insensitive)
    if detected == "hinglish" or lang_meta.get("contains_hinglish", False):
        sorted_translit = sorted(TRANSLITERATION_MAP.items(), key=lambda x: len(x[0]), reverse=True)
        lower_result = result.lower()
        for src, tgt in sorted_translit:
            if src in lower_result:
                # Find the position in the actual text (case-insensitive)
                idx = lower_result.find(src)
                if idx >= 0:
                    original_span = result[idx:idx + len(src)]
                    result = result[:idx] + tgt + result[idx + len(src):]
                    lower_result = result.lower()
                    records.append({"source": original_span, "target": tgt, "script": "hinglish"})

    return result, records


def normalize_multilingual_query(text: str) -> NormalizationResult:
    """
    Full multilingual query normalization pipeline.
    1. Detect language
    2. Transliterate non-English to English
    3. Record all transformations for provenance

    Returns NormalizationResult with original + normalized text.
    """
    if not text or not text.strip():
        return NormalizationResult(
            original_text=text or "",
            normalized_text=text or "",
            detected_language="en",
            language_confidence=0.0,
            normalization_confidence=0.0,
        )

    # Step 1: Language detection
    lang_meta = detect_language(text)

    # Step 2: Transliteration
    normalized, translit_records = transliterate_to_english(text, lang_meta)

    # Step 3: Clean up whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    # Step 4: Compute normalization confidence
    if lang_meta["detected"] == "en" and not lang_meta.get("is_multilingual"):
        norm_confidence = 0.99
    elif len(translit_records) > 0:
        norm_confidence = min(0.95, 0.70 + 0.05 * len(translit_records))
    else:
        norm_confidence = 0.80

    return NormalizationResult(
        original_text=text,
        normalized_text=normalized,
        detected_language=lang_meta["detected"],
        language_confidence=lang_meta["confidence"],
        transliterations_applied=translit_records,
        is_multilingual=lang_meta.get("is_multilingual", False),
        normalization_confidence=norm_confidence,
    )
