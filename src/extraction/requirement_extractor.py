"""
Procurement Requirement Extractor — StandSpec AI (Phase 6 / V1.3 Corrected)
Extracts structured technical requirements from raw procurement text into
a grounded NormalizedRequirementObject, strictly conforming to
schemas/normalized_requirement.schema.json.

Design laws:
1. Every extracted field MUST have:
   - value: extracted text
   - confidence: float (0.0 to 1.0)
   - source_span: exact substring in raw_text grounding the extraction
   - start_char: 0-indexed start character offset in raw_text
   - end_char: 0-indexed end character offset in raw_text
   - normalization: canonical representation or null
2. Never fabricate placeholder products (e.g. "General Procurement Item").
   If no product is grounded, product = None, product_status = "MISSING".
3. Deterministic hashing: input_hash = sha256(raw_text) ensures reproducibility.
4. Multi-occurrence capturing for voltages, dimensions, and capacities.
"""

import re
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

from src.extraction.normalizer import (
    detect_language,
    normalize_voltage,
    normalize_frequency,
    normalize_dimensions,
    normalize_temperature,
    normalize_material,
)

# ── Expanded Product Patterns Across All Procurement Domains ──

PRODUCT_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Electrotechnical: Cables & Conductors
    (re.compile(r'\b(xlpe\s+(?:insulated\s+)?(?:power\s+)?cable[s]?)\b', re.IGNORECASE), "Power Cable"),
    (re.compile(r'\b(pvc\s+(?:insulated\s+)?cable[s]?)\b', re.IGNORECASE), "Power Cable"),
    (re.compile(r'\b(underground\s+power\s+cable[s]?)\b', re.IGNORECASE), "Power Cable"),
    (re.compile(r'\b(aerial\s+bunched\s+cable[s]?|ab\s+cable[s]?)\b', re.IGNORECASE), "Aerial Bunched Cable"),
    (re.compile(r'\b(copper\s+and\s+(?:annealed\s+)?(aluminium|aluminum)\s+conductor[s]?\b)', re.IGNORECASE), "Copper Conductor Cable"),
    (re.compile(r'\b((?:bare\s+)?(?:annealed\s+)?(?:copper\s+and\s+)?(?:aluminium|aluminum)\s+conductor[s]?\b)', re.IGNORECASE), "Aluminium Conductor"),
    (re.compile(r'\b(copper\s+conductor(?:\s+.*cable)?|annealed\s+bare\s+copper\s+conductor[s]?|bare\s+copper\s+conductor[s]?)\b', re.IGNORECASE), "Copper Conductor Cable"),
    (re.compile(r'\b(electric\s+cable[s]?|power\s+cable[s]?)\b', re.IGNORECASE), "Power Cable"),
    (re.compile(r'\b(earthing\s+mat|grounding\s+system|earthing\s+system|earth\s+electrode[s]?)\b', re.IGNORECASE), "Earthing or Grounding System"),
    (re.compile(r'\b(electrical\s+installation(?:s)?\s+and\s+point\s+wiring|internal\s+electrical\s+wiring|wiring\s+installation[s]?)\b', re.IGNORECASE), "Electrical Installation Code"),

    # Electrotechnical: Transformers & Switchgear
    (re.compile(r'\b(autotransformer[s]?|power\s+transformer[s]?|distribution\s+transformer[s]?|transformer[s]?)\b', re.IGNORECASE), "Power Transformers"),
    (re.compile(r'\b(low[- ]voltage\s+switchgear|circuit[- ]breaker[s]?|mccb|acb|switchboard|distribution\s+board[s]?|dbo)\b', re.IGNORECASE), "Low-Voltage Switchgear and Controlgear"),
    (re.compile(r'\b(surge\s+arrester[s]?|lightning\s+arrester[s]?)\b', re.IGNORECASE), "Surge Arresters"),
    (re.compile(r'\b(induction\s+motor[s]?|three\s+phase\s+(?:ac\s+)?motor[s]?|electric\s+motor[s]?)\b', re.IGNORECASE), "Three Phase Induction Motors"),
    
    # Electrotechnical: Meters & Instrumentation
    (re.compile(r'\b(smart\s+(?:static\s+)?(?:electricity\s+)?meter[s]?|smart\s+meter[s]?|static\s+smart\s+meter[s]?)\b', re.IGNORECASE), "Smart Static Electricity Meters"),
    (re.compile(r'\b(static\s+(?:electronic\s+)?(?:energy|watthour|electricity)\s+meter[s]?)\b', re.IGNORECASE), "Static Energy Meters"),
    (re.compile(r'\b(induction\s+(?:type\s+)?(?:ac\s+)?(?:electricity|energy)\s+meter[s]?|electromechanical\s+meter[s]?)\b', re.IGNORECASE), "AC Electricity Meters Induction Type"),
    (re.compile(r'\b(energy\s+meter[s]?|electricity\s+meter[s]?)\b', re.IGNORECASE), "Electricity Meter"),
    (re.compile(r'\b(direct\s+reading\s+ph\s+meter[s]?|ph\s+meter[s]?)\b', re.IGNORECASE), "Direct Reading pH Meters"),
    (re.compile(r'\b(thermocouple\s+pyrometer[s]?|pyrometer[s]?)\b', re.IGNORECASE), "Thermocouple Pyrometers"),
    (re.compile(r'\b(bourdon\s+tube\s+.*pressure\s+gauge[s]?|pressure\s+and\s+vacuum\s+gauge[s]?|pressure\s+gauge[s]?|vacuum\s+gauge[s]?)\b', re.IGNORECASE), "Pressure and Vacuum Gauges"),
    
    # Electrotechnical: Domestic Appliances & Lighting
    (re.compile(r'\b(food\s+waste\s+disposer[s]?|waste\s+disposer[s]?)\b', re.IGNORECASE), "Food Waste Disposers Safety"),
    (re.compile(r'\b(self[- ]ballasted\s+led\s+lamp[s]?|led\s+lamp[s]?|led\s+bulb[s]?)\b', re.IGNORECASE), "Self-Ballasted LED Lamps"),
    (re.compile(r'\b(water\s+heater[s]?|geyser|household\s+(?:and\s+similar\s+)?electrical\s+appliance[s]?)\b', re.IGNORECASE), "Household Electrical Appliances"),
    (re.compile(r'\b((?:flush[- ]mounted\s+)?(?:piano\s+)?switch(?:es)?|tumbler\s+switch(?:es)?)\b', re.IGNORECASE), "Switches for Domestic and Similar Purposes"),
    (re.compile(r'\b(domestic\s+(?:electric\s+)?clothes\s+dryer[s]?|tumble\s+dryer[s]?)\b', re.IGNORECASE), "Electric Clothes Dryers"),
    (re.compile(r'\b((?:paper[- ]faced\s+)?gypsum\s+plaster\s+board[s]?|gypsum\s+board[s]?|plaster\s+board[s]?)\b', re.IGNORECASE), "Gypsum Plaster Boards"),
    
    # Civil Engineering: Piping & Fluid Transmission
    (re.compile(r'\b(?:high\s+density\s+polyethylene(?:\s*\([a-z0-9]+\))?(?:\s+(?:potable\s+)?water)?\s+pipe[s]?|hdpe(?:\s+(?:potable\s+)?water)?\s+pipe[s]?)\b', re.IGNORECASE), "HDPE Pipes for Water Supply"),
    (re.compile(r'\b(?:(?:unplasticized\s+)?polyvinyl\s+chloride(?:\s*\([a-z0-9]+\))?(?:\s+(?:potable\s+)?water)?\s+pipe[s]?|upvc(?:\s+(?:potable\s+)?water)?\s+pipe[s]?|pvc[- ]u(?:\s+(?:potable\s+)?water)?\s+pipe[s]?)\b', re.IGNORECASE), "uPVC Pipes for Potable Water Supplies"),
    (re.compile(r'\b(?:centrifugally\s+cast(?:\s*\([a-z0-9]+\))?\s+iron\s+pressure\s+pipe[s]?|spun\s+iron\s+pipe[s]?|cast\s+iron\s+pressure\s+pipe[s]?)\b', re.IGNORECASE), "Centrifugally Cast Iron Pressure Pipes"),
    (re.compile(r'\b(?:seamless\s+and\s+electric\s+resistance\s+welded(?:\s*\([a-z0-9]+\))?\s+.*steel\s+tube[s]?|mild\s+steel\s+tube[s]?|steel\s+tube[s]?|steel\s+tubular[s]?|erw\s+tube[s]?)\b', re.IGNORECASE), "Steel Tubes and Tubulars"),
    (re.compile(r'\b(pipe\s+fitting[s]?|cast\s+iron\s+fitting[s]?|upvc\s+fitting[s]?)\b', re.IGNORECASE), "Pipe Fittings"),
    (re.compile(r'\b(cast\s+iron\s+pipe[s]?|water\s+pipe[s]?)\b', re.IGNORECASE), "Pipes and Fittings"),
    (re.compile(r'\b(coarse\s+aggregate(?:\s*\([^)]*\))?)\b', re.IGNORECASE), "Coarse Aggregate"),
    (re.compile(r'\b(fine\s+aggregate(?:\s*\([^)]*\))?)\b', re.IGNORECASE), "Fine Aggregate"),

    # Civil Engineering: Cement & Concrete
    (re.compile(r'\b(rapid\s+hardening\s+(?:portland\s+)?cement|rhpc)\b', re.IGNORECASE), "Rapid Hardening Portland Cement"),
    (re.compile(r'\b(high\s+alumina\s+cement)\b', re.IGNORECASE), "High Alumina Cement"),
    (re.compile(r'\b(ordinary\s+portland\s+cement|opc)\b', re.IGNORECASE), "Ordinary Portland Cement"),
    (re.compile(r'\b(portland\s+pozzolana\s+cement|ppc)\b', re.IGNORECASE), "Portland Pozzolana Cement"),
    (re.compile(r'\b(portland\s+slag\s+cement|psc)\b', re.IGNORECASE), "Portland Slag Cement"),
    (re.compile(r'\b(ready\s+mixed\s+concrete|rmc)\b', re.IGNORECASE), "Ready Mixed Concrete"),
    (re.compile(r'\b(concrete\s+mix(?:\s+proportioning)?(?:\s+design)?)\b', re.IGNORECASE), "Concrete Mix Design"),
    (re.compile(r'(?<!solvent\s)(?<!quick\s)\b(cement)\b(?!\s+mortar\s+lining)', re.IGNORECASE), "Cement"),

    # Civil Engineering: Structural Steel & Building Codes
    (re.compile(r'\b(general\s+construction\s+in\s+steel(?:\s+code(?:\s+of\s+practice)?)?|structural\s+steel\s+code|structural\s+steel\s+building\s+frame[s]?|limit\s+state\s+design\s+.*steel)\b', re.IGNORECASE), "General Construction in Steel Code"),
    (re.compile(r'\b(structural\s+steel|tmt\s+(?:steel\s+)?rebars?|tmt\s+bars?|(?:high\s+strength\s+)?(?:ribbed\s+|deformed\s+)?(?:steel\s+)?reinforcement\s+bars?|steel\s+rebars?|rebars?)\b', re.IGNORECASE), "Steel Reinforcement Bars"),
    (re.compile(r'\b(seismic\s+design|ductile\s+design\s+and\s+detailing|earthquake\s+resistant\s+design)\b', re.IGNORECASE), "Seismic Design Code"),
    (re.compile(r'\b(design\s+(?:wind\s+)?pressure|wind\s+load\s+resistance|wind\s+loads?)\b', re.IGNORECASE), "Wind Load Design Code"),
    
    # Civil Engineering: Doors, Windows & Glass
    (re.compile(r'\b(upvc\s+(?:profile[s]?\s+)?(?:framed\s+)?(?:door[s]?|window[s]?|slider[s]?))\b', re.IGNORECASE), "uPVC Doors and Windows"),
    (re.compile(r'\b(safety\s+glass(?:ing)?|architectural\s+glass|glass\s+in\s+buildings?|glazing\s+materials?)\b', re.IGNORECASE), "Safety Glass and Glazing in Buildings"),
    (re.compile(r'\b(door[s]?\s*(?:and\s+)?window[s]?|flush\s+door[s]?|wooden\s+door[s]?|window\s+and\s+door|doors,\s*windows)\b', re.IGNORECASE), "Doors and Windows"),
    (re.compile(r'\b(transparent\s+float\s+glass|clear\s+float\s+glass|float\s+glass)\b', re.IGNORECASE), "Transparent Float Glass"),
    
    # Multilingual & Hinglish Patterns
    (re.compile(r'\b(?:paani\s+ka\s+pipe|paani\s+pipe|pani\s+ka\s+pipe|nal\s+ka\s+pipe)\b', re.IGNORECASE), "HDPE Pipes for Water Supply"),
    (re.compile(r'\b(?:bijli\s+(?:ka|ki|ke)\s+taar|bijli\s+taar|power\s+cable|underground\s+taar)\b', re.IGNORECASE), "Power Cable"),
    (re.compile(r'\b(?:bijli\s+(?:ka\s+)?transformer|substation\s+transformer)\b', re.IGNORECASE), "Distribution Transformers"),
    (re.compile(r'\b(?:tmt\s+sariya|lohe\s+ka\s+sariya|sariya|chhad)\b', re.IGNORECASE), "Steel Reinforcement Bars"),
    (re.compile(r'\b(?:cement\s+ki\s+bori|cement\s+bori|cement\s+ka\s+bag|cement\s+bag)\b', re.IGNORECASE), "Cement"),
    (re.compile(r'\b(?:flush\s+door|lakdi\s+ka\s+darwaja|darwaja|darwaza)\b', re.IGNORECASE), "Doors and Windows"),
    (re.compile(r'\b(?:led\s+batti|led\s+bulb|bulub)\b', re.IGNORECASE), "Self-Ballasted LED Lamps"),
    (re.compile(r'\b(?:bijli\s+ka\s+meter|smart\s+meter)\b', re.IGNORECASE), "Electricity Meter"),
    (re.compile(r'(?:थर्मोकपल\s+पायरोमीटर|पायरोमीटर)'), "Thermocouple Pyrometers"),
    (re.compile(r'(?:સેફ્ટી\s+ગ્લાસ|safety\s+glass)', re.IGNORECASE), "Safety Glass Architectural Building and General Uses"),
    (re.compile(r'(?:सौर\s+विकिरण|ऊर्जा\s+संरक्षण|energy\s+and\s+light)', re.IGNORECASE), "Use of Glass in Buildings Energy and Light"),
    (re.compile(r'(?:वितरण\s+ट्रांसफार्मर|ट्रांसफार्मर|ट्रान्सफ़ॉर्मर|ટ્રાન્સફોર્મર)'), "Distribution Transformers"),
    (re.compile(r'(?:ઇન્ડક્શન\s+મોટર્સ?|મોટર|પંપિંગ|मोटर|इंडक्शन)'), "Three Phase Induction Motors"),
    (re.compile(r'(?:બારણાં|દરવાજા|દરવાજાઓ|दरवाजे|खिड़कियां)'), "Doors and Windows"),
    (re.compile(r'(?:વિદ્યુત\s+કેબલ|તાર|केबल|तार)'), "Power Cable"),
    (re.compile(r'(?:સિમેન્ટ|કંક્રીટ|सीमेंट|कंक्रीट)'), "Cement and Concrete"),
]

# Attribute Extraction Patterns
VOLTAGE_PATTERN = re.compile(r'\b(\d+(?:\.\d+)?\s*(?:k?v|kilo\s*volts?))\b', re.IGNORECASE)
CURRENT_PATTERN = re.compile(r'\b(\d+(?:\.\d+)?\s*(?:a|amps?|amperes?))\b', re.IGNORECASE)
FREQUENCY_PATTERN = re.compile(r'\b(\d+(?:\.\d+)?\s*(?:hz|cycles\s*/\s*sec))\b', re.IGNORECASE)
DIMENSION_PATTERN = re.compile(
    r'\b('
    r'(?:\d+[\-\s]*(?:core|c)\s*(?:[xX*]\s*)?)?\d+(?:\.\d+)?\s*(?:sq\.?\s*mm|sqmm|mm2|mm²)'
    r'|\d+[\-\s]*(?:core|c)?\s*[xX*]\s*\d+(?:\.\d+)?\s*(?:sq\.?\s*mm|sqmm|mm2|mm²)?'
    r'|(?:dn|nb|diameter|od)\s*[:\-]?\s*\d+(?:\.\d+)?\s*(?:mm)?'
    r'|\d+(?:\.\d+)?\s*mm\s*(?:diameter|od|nb|dn)?'
    r')\b',
    re.IGNORECASE,
)
CAPACITY_PATTERN = re.compile(r'\b(\d+(?:\.\d+)?\s*(?:kva|mva|kw|mw|hp|bar|mpa|pn\s*\d+))\b', re.IGNORECASE)
TEMPERATURE_PATTERN = re.compile(r'\b(\d+(?:\.\d+)?\s*(?:°\s*C|deg(?:rees?)?\s*C|celsius))\b', re.IGNORECASE)
QUANTITY_PATTERN = re.compile(r'\b(\d+(?:,\d+)?\s*(?:meters?|mtrs?|km|units?|nos?|pieces?|tonnes?|mt))\b', re.IGNORECASE)

INSTALLATION_PATTERNS = [
    re.compile(r'\b(underground(?:\s+direct)?(?:\s+burial)?|direct\s+burial)\b', re.IGNORECASE),
    re.compile(r'\b(overhead|pole\s+mounted|plinth\s+mounted)\b', re.IGNORECASE),
    re.compile(r'\b(indoor(?:\s+wall\s+mounting)?|indoor\s+substation)\b', re.IGNORECASE),
    re.compile(r'\b(outdoor\s+installation|outdoor\s+substation)\b', re.IGNORECASE),
    re.compile(r'\b(under\s+kitchen\s+sink(?:\s+drainage)?|under-sink)\b', re.IGNORECASE),
    re.compile(r'\b(conduit|cable\s+tray)\b', re.IGNORECASE),
]

ENVIRONMENT_PATTERNS = [
    re.compile(r'\b(tropical(?:\s+wet\s+soil)?|tropical\s+climate)\b', re.IGNORECASE),
    re.compile(r'\b(corrosive|marine|saline\s+atmosphere)\b', re.IGNORECASE),
    re.compile(r'\b(high\s+ambient\s+temperature|submerged)\b', re.IGNORECASE),
    re.compile(r'\b(aggressive\s+chemical\s+environment[s]?)\b', re.IGNORECASE),
]

MATERIAL_PATTERNS = [
    re.compile(r'\b(crosslinked\s+polyethylene|xlpe)\b', re.IGNORECASE),
    re.compile(r'\b(polyvinyl\s+chloride|pvc|upvc|unplasticized\s+polyvinyl\s+chloride)\b', re.IGNORECASE),
    re.compile(r'\b(high\s+density\s+polyethylene|hdpe|pe[- ]100|pe[- ]80)\b', re.IGNORECASE),
    re.compile(r'\b(aluminium(?:\s+conductor)?|aluminum)\b', re.IGNORECASE),
    re.compile(r'\b(copper(?:\s+conductor)?)\b', re.IGNORECASE),
    re.compile(r'\b(centrifugally\s+cast\s+iron|spun\s+iron|cast\s+iron)\b', re.IGNORECASE),
    re.compile(r'\b(mild\s+steel|carbon\s+steel|stainless\s+steel\s*316|ss\s*316|stainless\s+steel)\b', re.IGNORECASE),
    re.compile(r'\b(galvanized\s+steel|gi\s+wire|gi\s+strip|hot[- ]dip\s+galvanized)\b', re.IGNORECASE),
]

GRADE_PATTERNS = [
    re.compile(r'\b(pe[- ]100|pe[- ]80)\b', re.IGNORECASE),
    re.compile(r'\b(pn\s*10|pn\s*6|pn\s*16|class\s*3|class\s*1\.0|class\s*0\.5)\b', re.IGNORECASE),
    re.compile(r'\b((?:33|43|53)\s*grade)\b', re.IGNORECASE),
    re.compile(r'\b(fe\s*(?:415|500|550)(?:d)?)\b', re.IGNORECASE),
    re.compile(r'\b(m(?:15|20|25|30|35|40))\b', re.IGNORECASE),
    re.compile(r'\b(heavy\s+class|medium\s+class|light\s+class)\b', re.IGNORECASE),
]

APPLICATION_PATTERNS = [
    re.compile(r'\b(potable\s+water(?:\s+distribution|\s+supply)?|drinking\s+water(?:\s+conveyance)?)\b', re.IGNORECASE),
    re.compile(r'\b(sewage\s+and\s+drainage|sewerage|non-potable)\b', re.IGNORECASE),
    re.compile(r'\b(industrial\s+water\s+and\s+gas\s+utility\s+piping|gas\s+pipeline\s+monitoring)\b', re.IGNORECASE),
    re.compile(r'\b(boiler\s+furnace|refractory\s+furnace\s+foundation[s]?)\b', re.IGNORECASE),
    re.compile(r'\b(advanced\s+metering\s+infrastructure|ami|utility\s+revenue\s+metering)\b', re.IGNORECASE),
    re.compile(r'\b(general\s+lighting\s+services)\b', re.IGNORECASE),
    re.compile(r'\b(kitchen\s+sink\s+organic\s+food\s+waste\s+disposal)\b', re.IGNORECASE),
]

SAFETY_PATTERNS = [
    re.compile(r'\b(ipx4|ip\s*\d{2})\b', re.IGNORECASE),
    re.compile(r'\b(safety\s+against\s+mechanical\s+jamming|mechanical\s+jamming)\b', re.IGNORECASE),
    re.compile(r'\b(electrical\s+safety|water\s+ingress)\b', re.IGNORECASE),
    re.compile(r'\b(frls|fire\s+retardant\s+low\s+smoke|flame\s+retardant)\b', re.IGNORECASE),
]

LOCATION_PATTERNS = [
    re.compile(r'\b(underground\s+rural|rural\s+potable|city\s+potable|substation|boiler\s+furnace|kitchen\s+sink)\b', re.IGNORECASE),
]

STANDARD_FAMILY_PATTERNS = [
    re.compile(r'\b(is\s*\d+(?:\s*\([^\)]+\))?(?::\d{4})?)\b', re.IGNORECASE),
    re.compile(r'\b(part\s*\d+(?:\s*section\s*\d+)?)\b', re.IGNORECASE),
]

TESTING_PATTERNS = [
    re.compile(r'\b(type\s+test(?:ed|ing)?)\b', re.IGNORECASE),
    re.compile(r'\b(routine\s+test(?:ed|ing)?)\b', re.IGNORECASE),
    re.compile(r'\b(acceptance\s+test(?:ed|ing)?)\b', re.IGNORECASE),
    re.compile(r'\b(spark\s+test)\b', re.IGNORECASE),
    re.compile(r'\b(is\s+10810(?:\s*\(part\s*\d+\))?)\b', re.IGNORECASE),
]

PERFORMANCE_PATTERNS = [
    re.compile(r'\b(frls|fire\s+retardant\s+low\s+smoke)\b', re.IGNORECASE),
    re.compile(r'\b(flame\s+retardant|fire\s+resistant)\b', re.IGNORECASE),
    re.compile(r'\b(high\s+tensile|weather\s+resistant)\b', re.IGNORECASE),
    re.compile(r'\b(luminous\s+efficacy\s*(?:>=|>|minimum)?\s*\d+\s*lm/w|power\s+factor\s*(?:>=|>)?\s*0\.\d+)\b', re.IGNORECASE),
]

MARKING_PATTERNS = [
    re.compile(r'\b(isi\s+mark(?:ing)?|bis\s+certification)\b', re.IGNORECASE),
    re.compile(r'\b(embossed|embossing|meter\s+marking)\b', re.IGNORECASE),
    re.compile(r'\b(batch\s+number|qr\s+code)\b', re.IGNORECASE),
]

TENDER_DATE_PATTERN = re.compile(
    r'\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',
    re.IGNORECASE,
)

# Declarative Registry for Engineering Discriminator Rules
DISCRIMINATOR_RULES: Dict[str, List[Dict[str, Any]]] = {
    "cable": [
        {"req_key": "voltage", "discriminator": "voltage_rating"},
        {"req_key": "dimensions", "discriminator": "conductor_cross_section_dimensions"},
        {"req_key": "material", "discriminator": "conductor_and_insulation_material"},
        {"req_key": "installation", "discriminator": "installation_type_aerial_vs_underground"},
    ],
    "cement": [
        {"req_key": "grade", "discriminator": "cement_grade_33_43_53", "condition": lambda p, r: "alumina" not in p},
        {"req_key": "material", "discriminator": "cement_type_opc_ppc_psc"},
    ],
    "transformer": [
        {"req_key": "voltage", "discriminator": "primary_and_secondary_voltage"},
        {"req_key": "capacity", "discriminator": "kva_capacity_rating"},
    ],
    "pipe": [
        {"req_key": "material", "discriminator": "pipe_material_hdpe_upvc_cast_iron"},
        {"req_key": "dimensions", "discriminator": "nominal_diameter_od_nb"},
    ],
    "steel": [
        {"req_key": "grade", "discriminator": "steel_grade_fe500_fe600"},
        {"req_key": "material", "discriminator": "steel_material_type"},
    ],
    "reinforcement": [
        {"req_key": "grade", "discriminator": "steel_grade_fe500_fe600"},
        {"req_key": "material", "discriminator": "steel_material_type"},
    ],
    "tmt": [
        {"req_key": "grade", "discriminator": "steel_grade_fe500_fe600"},
        {"req_key": "material", "discriminator": "steel_material_type"},
    ],
}


class RequirementExtractor:
    """
    Subsystem for extracting normalized, grounded requirements from procurement text.
    Every attribute contains value, confidence, exact source_span, start_char, and end_char.
    """

    EXTRACTOR_VERSION = "1.3.0"
    MODEL_VERSION = "deterministic-v1.3"

    def __init__(self):
        from src.extraction.modular_extractors import (
            ProductEntityExtractor,
            MaterialExtractor,
            ApplicationExtractor,
            ElectricalParameterExtractor,
            TechnologyModifierExtractor,
        )
        self.product_extractor = ProductEntityExtractor()
        self.material_extractor = MaterialExtractor()
        self.application_extractor = ApplicationExtractor()
        self.electrical_extractor = ElectricalParameterExtractor()
        self.modifier_extractor = TechnologyModifierExtractor()

    def extract(self, text: str, query_id: str = "Q_AUTO_001") -> Dict[str, Any]:
        """
        Extract requirements and return a dictionary conforming to
        schemas/normalized_requirement.schema.json.
        """
        raw_text = text.strip()
        lang_meta = detect_language(raw_text)
        input_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        requirements: Dict[str, Optional[Dict[str, Any]]] = {}

        # 1. Product extraction (Compositional Grammar + Pattern Fallback)
        # Avoid matching products on clearly out-of-domain text (e.g. food/bananas)
        ood_tokens = ["banana", "bananas", "fruit", "fruits", "mango", "wheat", "rice", "spice", "spices", "tea", "coffee"]
        is_food_ood = any(w in raw_text.lower() for w in ood_tokens) and not any(
            w in raw_text.lower() for w in ["cable", "pipe", "transformer", "breaker", "cement", "steel", "meter"]
        )

        product_field = None
        if not is_food_ood:
            # First check specific pattern list
            product_field = self._extract_first_match_with_offsets(
                raw_text,
                PRODUCT_PATTERNS,
                confidence=0.95,
                normalizer_func=lambda s, norm: norm,
            )
            # If not matched by fixed list, apply compositional entity grammar [material] + [modifier] + [noun]
            if not product_field:
                comp_prod = self.product_extractor.extract_compositional(raw_text)
                if comp_prod:
                    product_field = {
                        "value": comp_prod["value"],
                        "confidence": comp_prod["confidence"],
                        "source_span": comp_prod["source_span"],
                        "start_char": comp_prod["start_char"],
                        "end_char": comp_prod["end_char"],
                        "normalization": comp_prod["normalization"],
                        "base_product": comp_prod.get("base_product"),
                        "modifiers": comp_prod.get("modifiers", []),
                    }

        if product_field:
            requirements["product"] = product_field
            product_status = "EXTRACTED"
        else:
            # Corrective law: Never fabricate "General Procurement Item"
            requirements["product"] = None
            product_status = "MISSING"

        # 2. Voltage extraction (multi-voltage pair aware)
        volt_field = self.electrical_extractor.extract_voltages(raw_text)
        if volt_field:
            requirements["voltage"] = volt_field
        else:
            requirements["voltage"] = self._extract_regex_with_offsets(
                raw_text, VOLTAGE_PATTERN, confidence=0.98, normalizer_func=normalize_voltage
            )

        # 3. Dimensions extraction
        requirements["dimensions"] = self._extract_regex_with_offsets(
            raw_text, DIMENSION_PATTERN, confidence=0.95, normalizer_func=normalize_dimensions
        )

        # 4. Material extraction (Modular with Fallback)
        mat_field = self.material_extractor.extract(raw_text)
        if mat_field:
            requirements["material"] = mat_field
        else:
            requirements["material"] = self._extract_first_regex_with_offsets(
                raw_text, MATERIAL_PATTERNS, confidence=0.92, normalizer_func=normalize_material
            )

        # 5. Grade / Pressure Rating extraction
        grade_field = self._extract_first_regex_with_offsets(
            raw_text, GRADE_PATTERNS, confidence=0.90, normalizer_func=lambda s: s.upper()
        )
        if not grade_field:
            grade_field = self.electrical_extractor.extract_pressure_rating(raw_text)
        requirements["grade"] = grade_field

        # 6. Current extraction
        requirements["current"] = self._extract_regex_with_offsets(
            raw_text, CURRENT_PATTERN, confidence=0.95, normalizer_func=lambda s: s.upper()
        )

        # 7. Frequency extraction
        requirements["frequency"] = self._extract_regex_with_offsets(
            raw_text, FREQUENCY_PATTERN, confidence=0.95, normalizer_func=normalize_frequency
        )

        # 8. Capacity extraction
        cap_field = self.electrical_extractor.extract_capacity(raw_text)
        if cap_field:
            requirements["capacity"] = cap_field
        else:
            requirements["capacity"] = self._extract_regex_with_offsets(
                raw_text, CAPACITY_PATTERN, confidence=0.95, normalizer_func=lambda s: s.upper()
            )

        # 9. Temperature extraction
        requirements["temperature"] = self._extract_regex_with_offsets(
            raw_text, TEMPERATURE_PATTERN, confidence=0.95, normalizer_func=normalize_temperature
        )

        # 10. Installation extraction
        requirements["installation"] = self._extract_first_regex_with_offsets(
            raw_text, INSTALLATION_PATTERNS, confidence=0.88, normalizer_func=lambda s: s.lower()
        )

        # 11. Environment extraction
        requirements["environment"] = self._extract_first_regex_with_offsets(
            raw_text, ENVIRONMENT_PATTERNS, confidence=0.88, normalizer_func=lambda s: s.lower()
        )

        # 12. Application extraction (Modular with Fallback)
        app_field = self.application_extractor.extract(raw_text)
        if app_field:
            requirements["application"] = app_field
        else:
            requirements["application"] = self._extract_first_regex_with_offsets(
                raw_text, APPLICATION_PATTERNS, confidence=0.90, normalizer_func=lambda s: s.title()
            )

        # 13. Safety extraction
        requirements["safety"] = self._extract_first_regex_with_offsets(
            raw_text, SAFETY_PATTERNS, confidence=0.90, normalizer_func=lambda s: s.upper()
        )

        # 14. Performance extraction
        requirements["performance"] = self._extract_first_regex_with_offsets(
            raw_text, PERFORMANCE_PATTERNS, confidence=0.90, normalizer_func=lambda s: s.upper()
        )

        # 15. Testing extraction
        requirements["testing"] = self._extract_first_regex_with_offsets(
            raw_text, TESTING_PATTERNS, confidence=0.90, normalizer_func=lambda s: s.title()
        )

        # 16. Marking extraction
        requirements["marking"] = self._extract_first_regex_with_offsets(
            raw_text, MARKING_PATTERNS, confidence=0.90, normalizer_func=lambda s: s.title()
        )

        # 17. Quantity extraction
        requirements["quantity"] = self._extract_regex_with_offsets(
            raw_text, QUANTITY_PATTERN, confidence=0.92, normalizer_func=lambda s: s.lower()
        )

        # 18. Tender Date extraction
        requirements["tender_date"] = self._extract_regex_with_offsets(
            raw_text, TENDER_DATE_PATTERN, confidence=0.95, normalizer_func=None
        )

        # 19. Location extraction
        requirements["location"] = self._extract_first_regex_with_offsets(
            raw_text, LOCATION_PATTERNS, confidence=0.85, normalizer_func=lambda s: s.title()
        )

        # 20. Standard Family extraction
        requirements["standard_family"] = self._extract_first_regex_with_offsets(
            raw_text, STANDARD_FAMILY_PATTERNS, confidence=0.95, normalizer_func=lambda s: s.upper()
        )

        # 21. Normalized Procurement Intent Model (Phase C / C-1)
        procurement_intent = self._extract_procurement_intent(raw_text, requirements)

        # Determine missing discriminators for technical disambiguation
        missing_discriminators = self._identify_missing_discriminators(requirements, raw_text=raw_text)

        # Detect technical contradictions
        contradictions = self._detect_contradictions(raw_text, requirements)

        # 22. Query Sufficiency Assessment (Phase P1-A)
        query_sufficiency = self._evaluate_query_sufficiency(raw_text, requirements, missing_discriminators)
        if contradictions:
            query_sufficiency["contradictions"] = contradictions

        return {
            "query_id": query_id,
            "raw_text": raw_text,
            "language": lang_meta["detected"],
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "input_hash": input_hash,
            "extractor_version": self.EXTRACTOR_VERSION,
            "model_version": self.MODEL_VERSION,
            "extractor_mode": "DETERMINISTIC",
            "product_status": product_status,
            "requirements": requirements,
            "procurement_intent": procurement_intent,
            "query_sufficiency": query_sufficiency,
            "missing_discriminators": missing_discriminators,
            "contradictions": contradictions,
            "language_detection": lang_meta,
        }

    def _extract_regex_with_offsets(
        self, text: str, pattern: re.Pattern, confidence: float, normalizer_func=None
    ) -> Optional[Dict[str, Any]]:
        m = pattern.search(text)
        if not m:
            return None
        span_text = m.group(0)
        norm_val = normalizer_func(span_text) if normalizer_func else span_text
        return {
            "value": span_text,
            "confidence": confidence,
            "source_span": span_text,
            "start_char": m.start(),
            "end_char": m.end(),
            "normalization": norm_val,
        }

    def _extract_first_regex_with_offsets(
        self, text: str, patterns: List[re.Pattern], confidence: float, normalizer_func=None
    ) -> Optional[Dict[str, Any]]:
        for pat in patterns:
            res = self._extract_regex_with_offsets(text, pat, confidence, normalizer_func)
            if res:
                return res
        return None

    def _extract_first_match_with_offsets(
        self, text: str, pattern_list: List[Tuple[re.Pattern, str]], confidence: float, normalizer_func=None
    ) -> Optional[Dict[str, Any]]:
        for pat, norm in pattern_list:
            m = pat.search(text)
            if m:
                span_text = m.group(0)
                norm_val = normalizer_func(span_text, norm) if normalizer_func else norm
                return {
                    "value": span_text,
                    "confidence": confidence,
                    "source_span": span_text,
                    "start_char": m.start(),
                    "end_char": m.end(),
                    "normalization": norm_val,
                }
        return None

    def _identify_missing_discriminators(
        self, reqs: Dict[str, Optional[Dict[str, Any]]], raw_text: str = ""
    ) -> List[str]:
        """
        Flag missing discriminators necessary for unambiguous standard selection.
        Uses declarative DISCRIMINATOR_RULES registry and supports multi-product clauses.
        """
        missing = []
        product_val = ((reqs.get("product") or {}).get("value") or "").lower()
        search_target = f"{product_val} {raw_text.lower()}".strip()

        matched_categories = []
        for cat in DISCRIMINATOR_RULES:
            if cat in product_val:
                matched_categories.append(cat)
            elif cat in search_target and not matched_categories:
                matched_categories.append(cat)

        seen_discriminators = set()
        for cat in matched_categories:
            for rule in DISCRIMINATOR_RULES.get(cat, []):
                req_key = rule["req_key"]
                disc = rule["discriminator"]
                cond = rule.get("condition")
                if cond and not cond(product_val, reqs):
                    continue
                if not reqs.get(req_key) and disc not in seen_discriminators:
                    missing.append(disc)
                    seen_discriminators.add(disc)

        return missing

    def _detect_contradictions(self, raw_text: str, requirements: dict) -> List[str]:
        """
        Detect technical contradictions in procurement requirements without forcing resolution.
        Delegates to authoritative RequirementConsistencyGate (Mentor review Part 3).
        """
        from src.recommendation.consistency_gate import RequirementConsistencyGate
        res = RequirementConsistencyGate.check(raw_text, requirements=requirements)
        return [c.description for c in res.contradictions]

    def _extract_procurement_intent(self, raw_text: str, requirements: dict) -> dict:
        """Extract procurement object, object type, and technical intent (Phase P1-A)."""
        q_lower = raw_text.lower()
        prod_obj = requirements.get("product")
        prod_val = (prod_obj.get("normalization") or prod_obj.get("value")) if prod_obj else None

        # Fail-closed procurement object: never slice raw_text when unknown
        if not prod_val:
            proc_obj = {
                "state": "UNKNOWN",
                "value": None,
                "confidence": 0.0,
                "evidence_span": [],
            }
        else:
            proc_obj = {
                "state": "EXTRACTED",
                "value": prod_val,
                "confidence": prod_obj.get("confidence", 0.95),
                "evidence_span": [prod_obj.get("start_char", 0), prod_obj.get("end_char", 0)],
            }

        # Technical Intent
        has_supply = any(w in q_lower for w in ["supply", "procure", "procurement", "purchase", "delivery"])
        has_install = any(w in q_lower for w in ["installation", "install", "laying", "erection"])
        has_design = any(w in q_lower for w in ["design", "proportioning", "detailing"])
        has_testing = any(w in q_lower for w in ["testing", "test of", "analysis of"])

        if has_supply and has_install:
            tech_intent = "SUPPLY_AND_INSTALLATION"
        elif has_install:
            tech_intent = "INSTALLATION"
        elif has_design:
            tech_intent = "DESIGN"
        elif has_testing:
            tech_intent = "TESTING"
        else:
            tech_intent = "SUPPLY"

        # Object Type
        # Apparatus / Equipment: circuit breakers, MCCBs, transformers, motors, pumps, cables
        if any(w in q_lower for w in ["circuit breaker", "circuit-breaker", "mccb", "acb", "vcb", "transformer", "motor", "pump", "cable"]):
            obj_type = "FINISHED_PRODUCT"
        # Assemblies: windows, doors, switchgear panels, distribution panels, substations
        elif any(w in q_lower for w in ["door", "window", "slider", "panel", "switchboard", "substation", "cubicle"]):
            if any(w in q_lower for w in ["profile for", "profiles for", "only profile"]):
                obj_type = "COMPONENT"
            else:
                obj_type = "FINISHED_ASSEMBLY"
        # Components: fittings, gaskets, joints, rails, terminals, profiles
        elif any(w in q_lower for w in ["profile", "profiles", "gasket", "mounting rail", "din rail", "fitting", "joint"]):
            obj_type = "COMPONENT"
        # Raw materials: cement, aggregate, sand, bitumen
        elif any(w in q_lower for w in ["cement", "aggregate", "sand", "bitumen", "gravel"]):
            obj_type = "RAW_MATERIAL"
        # Services
        elif has_install and not has_supply:
            obj_type = "INSTALLATION_SERVICE"
        elif has_design and not has_supply:
            obj_type = "DESIGN_ACTIVITY"
        elif has_testing and not has_supply:
            obj_type = "TESTING_SERVICE"
        else:
            obj_type = "FINISHED_PRODUCT"

        return {
            "procurement_object": proc_obj,
            "object_type": obj_type,
            "technical_intent": tech_intent,
        }

    def _evaluate_query_sufficiency(
        self,
        raw_text: str,
        requirements: dict,
        missing_discriminators: list,
    ) -> dict:
        """
        Evaluates technical query sufficiency before retrieval / recommendation (P1-A).
        """
        prod = requirements.get("product")
        has_product = bool(prod and prod.get("value"))
        desig_matches = requirements.get("standard_family")
        has_explicit_desig = bool(desig_matches and desig_matches.get("value"))

        has_params = any(
            requirements.get(k) is not None
            for k in ["voltage", "dimensions", "material", "grade", "capacity", "application"]
        )

        is_underspecified = (
            not has_explicit_desig
            and (
                not has_product
                or (not has_params and len(missing_discriminators) >= 2)
            )
        )

        if is_underspecified:
            state = "INSUFFICIENT"
            reason = (
                f"Procurement query is under-specified. Critical discriminators missing: "
                f"{', '.join(missing_discriminators) if missing_discriminators else 'Product undefined'}. "
                f"Detailed tender parameters are required to distinguish applicable standards."
            )
        elif missing_discriminators:
            state = "PARTIALLY_SPECIFIED"
            reason = f"Key parameters present, but technical disambiguation recommended for: {', '.join(missing_discriminators)}"
        else:
            state = "SUFFICIENT"
            reason = "Query contains sufficient technical specifications for standard evaluation."

        return {
            "state": state,
            "is_sufficient": state in ("SUFFICIENT", "PARTIALLY_SPECIFIED") or has_explicit_desig,
            "product_identified": has_product,
            "critical_discriminators_present": len(missing_discriminators) == 0,
            "missing_critical_discriminators": missing_discriminators,
            "specific_standard_requested": has_explicit_desig,
            "reason": reason,
        }
