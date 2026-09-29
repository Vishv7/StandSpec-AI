"""
Modular Extractors for Open-World Procurement Queries — StandSpec AI (Phase P1-E Section 5).

Implements compositional extraction:
- ProductEntityExtractor: Compositional grammar [material] + [technology/modifier] + [product] + [variant]
- MaterialExtractor: Comprehensive material and polymer taxonomy
- ApplicationExtractor: Multi-domain context and intended usage
- ElectricalParameterExtractor: Multi-value voltage pairs (e.g. 33/11 kV), capacities, current ranges
- DimensionExtractor: Diameters, core counts, cross-sectional areas
- TechnologyModifierExtractor: Technical modifiers (smart, whole-current, molded-case, underground, etc.)
- IntentExtractor: Procurement object classification and technical intent
- DesignationExtractor: Explicit standard citations (e.g. IS 4984, IS 1180)
"""

import re
from typing import Dict, Any, List, Optional, Tuple


class TechnologyModifierExtractor:
    """Extracts and normalizes technical modifiers across electrical, mechanical, and civil domains."""

    MODIFIER_PATTERNS = [
        # Metering modifiers
        (re.compile(r'\b(smart)\b', re.IGNORECASE), "smart"),
        (re.compile(r'\b(prepaid|pre-paid)\b', re.IGNORECASE), "prepaid"),
        (re.compile(r'\b(ami|advanced\s+metering\s+infrastructure)\b', re.IGNORECASE), "AMI"),
        (re.compile(r'\b(cellular|gprs|4g|nb-iot|lte)\b', re.IGNORECASE), "cellular"),
        (re.compile(r'\b(rf\s+mesh|radio\s+frequency)\b', re.IGNORECASE), "rf_mesh"),
        (re.compile(r'\b(direct[- ]connected|whole[- ]current)\b', re.IGNORECASE), "whole-current"),
        (re.compile(r'\b(ct[- ]operated|current\s+transformer\s+operated)\b', re.IGNORECASE), "CT-operated"),
        (re.compile(r'\b(pt[- ]operated|potential\s+transformer\s+operated|ct/pt[- ]operated)\b', re.IGNORECASE), "PT-operated"),

        # Switchgear modifiers
        (re.compile(r'\b(moulded[- ]case|molded[- ]case|mccb)\b', re.IGNORECASE), "molded-case"),
        (re.compile(r'\b(air[- ]circuit[- ]breaker|acb)\b', re.IGNORECASE), "air-circuit-breaker"),
        (re.compile(r'\b(vacuum[- ]circuit[- ]breaker|vcb)\b', re.IGNORECASE), "vacuum"),
        (re.compile(r'\b(gas[- ]insulated|gis)\b', re.IGNORECASE), "gas-insulated"),
        (re.compile(r'\b(miniature\s+circuit\s+breaker|mcb)\b', re.IGNORECASE), "miniature"),

        # Cable & Conductor modifiers
        (re.compile(r'\b(underground|direct\s+burial)\b', re.IGNORECASE), "underground"),
        (re.compile(r'\b(aerial|overhead|pole[- ]mounted)\b', re.IGNORECASE), "aerial"),
        (re.compile(r'\b(armoured|armored)\b', re.IGNORECASE), "armoured"),
        (re.compile(r'\b(unarmoured|unarmored)\b', re.IGNORECASE), "unarmoured"),
        (re.compile(r'\b(heavy[- ]duty)\b', re.IGNORECASE), "heavy-duty"),
        (re.compile(r'\b(cross[- ]linked|crosslinked)\b', re.IGNORECASE), "cross-linked"),

        # Piping & Mechanical modifiers
        (re.compile(r'\b(pressure)\b', re.IGNORECASE), "pressure"),
        (re.compile(r'\b(casing)\b', re.IGNORECASE), "casing"),
        (re.compile(r'\b(centrifugally\s+cast|spun)\b', re.IGNORECASE), "spun"),
        (re.compile(r'\b(seamless)\b', re.IGNORECASE), "seamless"),
        (re.compile(r'\b(erw|electric\s+resistance\s+welded)\b', re.IGNORECASE), "erw"),

        # General operational
        (re.compile(r'\b(portable)\b', re.IGNORECASE), "portable"),
        (re.compile(r'\b(automatic)\b', re.IGNORECASE), "automatic"),
        (re.compile(r'\b(manual)\b', re.IGNORECASE), "manual"),
        (re.compile(r'\b(dry[- ]type)\b', re.IGNORECASE), "dry-type"),
        (re.compile(r'\b(oil[- ]immersed|oil[- ]cooled)\b', re.IGNORECASE), "oil-immersed"),
    ]

    def extract(self, text: str) -> List[Dict[str, Any]]:
        found = []
        seen = set()
        for pat, norm in self.MODIFIER_PATTERNS:
            for m in pat.finditer(text):
                if norm not in seen:
                    seen.add(norm)
                    found.append({
                        "value": m.group(0),
                        "normalized": norm,
                        "start": m.start(),
                        "end": m.end(),
                    })
        return found


class MaterialExtractor:
    """Extracts material types with robust synonym recognition."""

    MATERIAL_RULES = [
        # Polymers
        (re.compile(r'\b(cross[- ]linked\s+polyethylene|crosslinked\s+polyethylene|xlpe)\b', re.IGNORECASE), "XLPE"),
        (re.compile(r'\b(high\s+density\s+polyethylene|hdpe|pe[- ]?100|pe[- ]?80)\b', re.IGNORECASE), "HDPE"),
        (re.compile(r'\b(medium\s+density\s+polyethylene|mdpe)\b', re.IGNORECASE), "MDPE"),
        (re.compile(r'\b(low\s+density\s+polyethylene|ldpe)\b', re.IGNORECASE), "LDPE"),
        (re.compile(r'\b(polyethylene|pe)\b', re.IGNORECASE), "Polyethylene"),
        (re.compile(r'\b(unplasticized\s+polyvinyl\s+chloride|upvc|pvc[- ]u)\b', re.IGNORECASE), "uPVC"),
        (re.compile(r'\b(polyvinyl\s+chloride|pvc)\b', re.IGNORECASE), "PVC"),
        (re.compile(r'\b(chlorinated\s+polyvinyl\s+chloride|cpvc)\b', re.IGNORECASE), "CPVC"),

        # Metals
        (re.compile(r'\b(centrifugally\s+cast\s+iron|spun\s+cast\s+iron|spun\s+iron|ductile\s+iron|cast\s+iron)\b', re.IGNORECASE), "Cast Iron"),
        (re.compile(r'\b(mild\s+steel|carbon\s+steel)\b', re.IGNORECASE), "Mild Steel"),
        (re.compile(r'\b(stainless\s+steel(?:\s*316|\s*304)?|ss\s*316|ss\s*304)\b', re.IGNORECASE), "Stainless Steel"),
        (re.compile(r'\b(galvanized\s+steel|galvanised\s+iron|gi\s+wire|gi\s+strip|hot[- ]dip\s+galvanized)\b', re.IGNORECASE), "Galvanized Steel"),
        (re.compile(r'\b(structural\s+steel)\b', re.IGNORECASE), "Structural Steel"),
        (re.compile(r'\b(steel)\b', re.IGNORECASE), "Steel"),
        (re.compile(r'\b(annealed\s+copper|electrolytic\s+copper|bare\s+copper|copper)\b', re.IGNORECASE), "Copper"),
        (re.compile(r'\b(aluminium\s+alloy|aluminium|aluminum|acsr|aaac)\b', re.IGNORECASE), "Aluminium"),

        # Cementitious & Glass
        (re.compile(r'\b(ordinary\s+portland\s+cement|opc)\b', re.IGNORECASE), "OPC"),
        (re.compile(r'\b(portland\s+pozzolana\s+cement|ppc)\b', re.IGNORECASE), "PPC"),
        (re.compile(r'\b(portland\s+slag\s+cement|psc)\b', re.IGNORECASE), "PSC"),
        (re.compile(r'\b(high\s+alumina\s+cement)\b', re.IGNORECASE), "High Alumina Cement"),
        (re.compile(r'\b(cement)\b', re.IGNORECASE), "Cement"),
        (re.compile(r'\b(ready\s+mixed\s+concrete|rmc|reinforced\s+concrete|concrete)\b', re.IGNORECASE), "Concrete"),
        (re.compile(r'\b(transparent\s+float\s+glass|clear\s+float\s+glass|float\s+glass|toughened\s+glass|safety\s+glass|glass)\b', re.IGNORECASE), "Glass"),
    ]

    def extract(self, text: str) -> Optional[Dict[str, Any]]:
        for pat, norm in self.MATERIAL_RULES:
            m = pat.search(text)
            if m:
                return {
                    "value": m.group(0),
                    "normalization": norm,
                    "confidence": 0.95,
                    "source_span": m.group(0),
                    "start_char": m.start(),
                    "end_char": m.end(),
                }
        return None


class ElectricalParameterExtractor:
    """Extracts electrical parameters with multi-voltage pair support."""

    VOLTAGE_PAIR_PATTERN = re.compile(
        r'\b(\d+(?:\.\d+)?)\s*(?:/|\s+to\s+)\s*(\d+(?:\.\d+)?)\s*(k?v|kilo\s*volts?)\b',
        re.IGNORECASE,
    )
    VOLTAGE_SINGLE_PATTERN = re.compile(
        r'\b(\d+(?:\.\d+)?)\s*(k?v|kilo\s*volts?|volts?)\b',
        re.IGNORECASE,
    )
    CAPACITY_PATTERN = re.compile(
        r'\b(\d+(?:\.\d+)?)\s*(kva|mva|kw|mw|hp)\b',
        re.IGNORECASE,
    )
    PRESSURE_RATING_PATTERN = re.compile(
        r'\b(pn\s*\d+|class\s*\d+|\d+(?:\.\d+)?\s*(?:bar|mpa|kgf/cm²))\b',
        re.IGNORECASE,
    )

    def extract_voltages(self, text: str) -> Optional[Dict[str, Any]]:
        # First check for voltage pairs like "33/11 kV"
        pair_match = self.VOLTAGE_PAIR_PATTERN.search(text)
        if pair_match:
            v1_str, v2_str, unit = pair_match.groups()
            v1 = float(v1_str)
            v2 = float(v2_str)
            # High side is the larger number
            high_val = max(v1, v2)
            low_val = min(v1, v2)
            unit_norm = "kV" if "k" in unit.lower() else "V"

            return {
                "value": pair_match.group(0),
                "confidence": 0.98,
                "source_span": pair_match.group(0),
                "start_char": pair_match.start(),
                "end_char": pair_match.end(),
                "normalization": f"{high_val:g}/{low_val:g} {unit_norm}",
                "voltage_pairs": [
                    {"side": "HIGH", "value": f"{high_val:g} {unit_norm}"},
                    {"side": "LOW", "value": f"{low_val:g} {unit_norm}"},
                ],
                "high_side": f"{high_val:g} {unit_norm}",
                "low_side": f"{low_val:g} {unit_norm}",
            }

        # Otherwise look for single voltage
        single_match = self.VOLTAGE_SINGLE_PATTERN.search(text)
        if single_match:
            val_str, unit = single_match.groups()
            val = float(val_str)
            unit_lower = unit.lower()
            if "k" in unit_lower:
                norm_str = f"{int(val * 1000)} V" if val < 10 else f"{val:g} kV"
            else:
                norm_str = f"{val:g} V"

            return {
                "value": single_match.group(0),
                "confidence": 0.95,
                "source_span": single_match.group(0),
                "start_char": single_match.start(),
                "end_char": single_match.end(),
                "normalization": norm_str,
            }
        return None

    def extract_capacity(self, text: str) -> Optional[Dict[str, Any]]:
        m = self.CAPACITY_PATTERN.search(text)
        if m:
            val_str, unit = m.groups()
            return {
                "value": m.group(0),
                "confidence": 0.95,
                "source_span": m.group(0),
                "start_char": m.start(),
                "end_char": m.end(),
                "normalization": f"{val_str} {unit.upper()}",
            }
        return None

    def extract_pressure_rating(self, text: str) -> Optional[Dict[str, Any]]:
        m = self.PRESSURE_RATING_PATTERN.search(text)
        if m:
            val = m.group(0)
            norm = re.sub(r'\s+', '', val.upper())
            return {
                "value": val,
                "confidence": 0.92,
                "source_span": val,
                "start_char": m.start(),
                "end_char": m.end(),
                "normalization": norm,
            }
        return None


class ApplicationExtractor:
    """Extracts application and municipal/industrial context."""

    APPLICATION_PATTERNS = [
        (re.compile(r'\b(potable\s+water(?:\s+distribution|\s+supply)?|drinking\s+water(?:\s+distribution|\s+supply|\s+conveyance)?)\b', re.IGNORECASE), "Potable Water Distribution"),
        (re.compile(r'\b(agricultural\s+drainage|farm\s+drainage)\b', re.IGNORECASE), "Agricultural Drainage"),
        (re.compile(r'\b(sewage\s+and\s+drainage|sewerage|non-potable|drainage(?:\s+without\s+fittings)?)\b', re.IGNORECASE), "Sewage and Drainage"),
        (re.compile(r'\b(substation\s+use|substation|indoor\s+substation|outdoor\s+substation)\b', re.IGNORECASE), "Substation Use"),
        (re.compile(r'\b(underground\s+distribution|underground\s+installation|underground\s+feeder)\b', re.IGNORECASE), "Underground Power Distribution"),
        (re.compile(r'\b(overhead\s+transmission|overhead\s+distribution)\b', re.IGNORECASE), "Overhead Power Transmission"),
        (re.compile(r'\b(advanced\s+metering\s+infrastructure|ami|utility\s+revenue\s+metering|smart\s+metering)\b', re.IGNORECASE), "AMI Utility Revenue Metering"),
        (re.compile(r'\b(municipal\s+water\s+and\s+sewage|municipal\s+water)\b', re.IGNORECASE), "Municipal Water and Sewage"),
        (re.compile(r'\b(general\s+lighting\s+services|street\s+lighting)\b', re.IGNORECASE), "Street and General Lighting"),
        (re.compile(r'\b(rcc\s+construction|concrete\s+reinforcement|structural\s+framework)\b', re.IGNORECASE), "Concrete Reinforcement Construction"),
    ]

    def extract(self, text: str) -> Optional[Dict[str, Any]]:
        for pat, norm in self.APPLICATION_PATTERNS:
            m = pat.search(text)
            if m:
                return {
                    "value": m.group(0),
                    "normalization": norm,
                    "confidence": 0.92,
                    "source_span": m.group(0),
                    "start_char": m.start(),
                    "end_char": m.end(),
                }
        return None


class ProductEntityExtractor:
    """
    Compositional product grammar parser:
    [material] + [technology/modifier] + [product_noun] + [variant]
    Disassembles compound noun phrases into structured procurement objects.
    """

    PRODUCT_NOUN_PATTERNS = [
        # Pipes & Tubes
        (re.compile(r'\b(pressure\s+pipe[s]?)\b', re.IGNORECASE), "Pressure Pipes"),
        (re.compile(r'\b(casing\s+pipe[s]?)\b', re.IGNORECASE), "Casing Pipes"),
        (re.compile(r'\b(pipe[s]?|piping)\b', re.IGNORECASE), "Pipes"),
        (re.compile(r'\b(tube[s]?|tubular[s]?)\b', re.IGNORECASE), "Tubes and Tubulars"),
        (re.compile(r'\b(pipe\s+fitting[s]?|fitting[s]?)\b', re.IGNORECASE), "Pipe Fittings"),

        # Cables & Conductors
        (re.compile(r'\b(power\s+cable[s]?)\b', re.IGNORECASE), "Power Cable"),
        (re.compile(r'\b(control\s+cable[s]?)\b', re.IGNORECASE), "Control Cable"),
        (re.compile(r'\b(aerial\s+bunched\s+cable[s]?|ab\s+cable[s]?)\b', re.IGNORECASE), "Aerial Bunched Cable"),
        (re.compile(r'\b(cable[s]?)\b', re.IGNORECASE), "Power Cable"),
        (re.compile(r'\b(conductor[s]?)\b', re.IGNORECASE), "Conductors"),

        # Transformers
        (re.compile(r'\b(power\s+transformer[s]?)\b', re.IGNORECASE), "Power Transformers"),
        (re.compile(r'\b(distribution\s+transformer[s]?)\b', re.IGNORECASE), "Distribution Transformers"),
        (re.compile(r'\b(autotransformer[s]?)\b', re.IGNORECASE), "Autotransformers"),
        (re.compile(r'\b(transformer[s]?)\b', re.IGNORECASE), "Transformers"),

        # Switchgear
        (re.compile(r'\b(circuit[- ]breaker[s]?|mccb|acb|vcb)\b', re.IGNORECASE), "Circuit Breakers"),
        (re.compile(r'\b(switchgear|controlgear|switchboard|distribution\s+board[s]?)\b', re.IGNORECASE), "Switchgear and Controlgear"),
        (re.compile(r'\b(surge\s+arrester[s]?|lightning\s+arrester[s]?)\b', re.IGNORECASE), "Surge Arresters"),

        # Meters
        (re.compile(r'\b(electricity\s+meter[s]?|energy\s+meter[s]?|watthour\s+meter[s]?|smart\s+meter[s]?)\b', re.IGNORECASE), "Electricity Meters"),
        (re.compile(r'\b(meter[s]?)\b', re.IGNORECASE), "Meters"),

        # Motors
        (re.compile(r'\b(induction\s+motor[s]?|motor[s]?)\b', re.IGNORECASE), "Induction Motors"),

        # Cement, Concrete & Steel
        (re.compile(r'\b(cement)\b', re.IGNORECASE), "Cement"),
        (re.compile(r'\b(concrete)\b', re.IGNORECASE), "Concrete"),
        (re.compile(r'\b(tmt\s+bars?|reinforcement\s+bars?|deformed\s+steel\s+bars?)\b', re.IGNORECASE), "Steel Reinforcement Bars"),
        (re.compile(r'\b(structural\s+steel)\b', re.IGNORECASE), "Structural Steel"),

        # Doors, Windows, Glass
        (re.compile(r'\b(door[s]?|window[s]?|slider[s]?)\b', re.IGNORECASE), "Doors and Windows"),
        (re.compile(r'\b(safety\s+glass|float\s+glass|glass)\b', re.IGNORECASE), "Glass"),
    ]

    def __init__(self):
        self.modifier_extractor = TechnologyModifierExtractor()
        self.material_extractor = MaterialExtractor()

    def extract_compositional(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parses text into a compositional product entity:
        e.g. "polyethylene pressure pipes" ->
             product = "Pipes", material = "Polyethylene", variant = "pressure"
        """
        # 1. Search for product noun
        matched_noun = None
        matched_span = None
        matched_offsets = None

        for pat, norm in self.PRODUCT_NOUN_PATTERNS:
            m = pat.search(text)
            if m:
                matched_noun = norm
                matched_span = m.group(0)
                matched_offsets = (m.start(), m.end())
                break

        if not matched_noun:
            return None

        # 2. Search for material
        mat_info = self.material_extractor.extract(text)
        mat_name = mat_info["normalization"] if mat_info else None

        # 3. Search for modifiers
        mods = self.modifier_extractor.extract(text)
        mod_names = [m["normalized"] for m in mods]

        # 4. Synthesize canonical product title
        # e.g. Polyethylene + Pressure + Pipes -> "Polyethylene Pressure Pipes"
        prefix_parts = []
        if mat_name and mat_name.lower() not in matched_noun.lower():
            prefix_parts.append(mat_name)
        for mod in mod_names:
            if mod.lower() not in matched_noun.lower() and (not mat_name or mod.lower() not in mat_name.lower()):
                prefix_parts.append(mod.title())

        if prefix_parts:
            canonical_name = f"{' '.join(prefix_parts)} {matched_noun}".strip()
        else:
            canonical_name = matched_noun

        # Compute full span bounding box if material/modifiers are adjacent
        start_char = matched_offsets[0]
        end_char = matched_offsets[1]
        if mat_info and mat_info["start_char"] < start_char:
            start_char = mat_info["start_char"]
        if mat_info and mat_info["end_char"] > end_char:
            end_char = mat_info["end_char"]
        for mod in mods:
            if mod["start"] < start_char:
                start_char = mod["start"]
            if mod["end"] > end_char:
                end_char = mod["end"]

        source_span = text[start_char:end_char]

        return {
            "value": source_span,
            "normalization": canonical_name,
            "base_product": matched_noun,
            "material": mat_name,
            "modifiers": mod_names,
            "confidence": 0.95,
            "source_span": source_span,
            "start_char": start_char,
            "end_char": end_char,
        }
