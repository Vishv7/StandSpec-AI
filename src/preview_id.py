"""
Preview-ID generator and canonical standard identity parser for BIS standards.
Phase 2 of the BIS Standards Data Collector.

Converts BIS standard numbers to canonical identity structures and preview IDs used by:
    https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=<preview_id>

Confirmed mappings (from COLLECTOR_CONTEXT.md §3.1):
    IS 19901:2026                           -> 19901_2026
    IS 19897:2026                           -> 19897_2026
    IS 17874 (Part 2):2026                  -> 17874_2_2026
    IS 302 (Part 2/Sec 16):2026             -> 302_2_16_2026
    IS/IEC/IEEE 60079 (Part 30/Sec 2):2015  -> iee60079_30_2_2015  (prefix pattern)
"""

import re
import logging
import csv
from pathlib import Path

logger = logging.getLogger(__name__)

# BSB Edge preview URL template
PREVIEW_URL_TEMPLATE = "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id={preview_id}"

# Recognized standard families in order of specificity (longest match first)
KNOWN_FAMILIES = [
    "IS/IEC/IEEE",
    "IS/IEC/TS",
    "IS/IEC/TR",
    "IS/ISO/IEC",
    "IS/IEC",
    "IS/ISO",
    "IS",
    "ISO/IEC GUIDE",
    "ISO/IEC",
    "ISO/TS",
    "ISO",
    "IEC",
    "SP",
]

# BSB Edge preview ID prefix mapping.
# Some international-adoption families use a prefix before the base number.
# Discovered empirically: IS/IEC/IEEE 60079 (Part 30/Sec 2):2015 -> iee60079_30_2_2015
FAMILY_PREFIX_MAP = {
    "IS/IEC/IEEE": "iee",
    # Most IS/IEC, IS/ISO, IS/ISO/IEC standards don't have previews,
    # but when they do, the prefix pattern is tried as a candidate.
    "IS/IEC/TS": "iec",
    "IS/IEC/TR": "iec",
    "IS/IEC": "iec",
    "IS/ISO": "iso",
    "IS/ISO/IEC": "isoiec",
}


def parse_standard_identity(standard_str: str) -> dict | None:
    """
    Parse a raw standard string into its canonical standard identity.
    
    Returns a dict with:
        standard_designation: str (e.g. 'IS 302 (Part 2/Sec 16):2026')
        family: str               (e.g. 'IS', 'IS/IEC', 'SP')
        base_number: str          (e.g. '302', '60079', '45')
        part: str | None          (e.g. '2', '29')
        section: str | None       (e.g. '16', '2')
        year: str | None          (e.g. '2026', '2015')
    or None if the string is not a recognized standard format.
    """
    if not standard_str or not isinstance(standard_str, str):
        return None
    
    s = standard_str.strip()
    # Normalize multiple whitespace characters to single space
    s = re.sub(r'\s+', ' ', s)
    
    # Identify family prefix (longest match first)
    matched_family = None
    remainder = s
    for family in KNOWN_FAMILIES:
        # Check if s starts with family followed by space or number
        pattern = r'^' + re.escape(family) + r'(?:\s+|\b)(.*)$'
        m = re.match(pattern, s, re.IGNORECASE)
        if m:
            matched_family = family
            remainder = m.group(1).strip()
            break
            
    if not matched_family:
        return None
        
    # Parse base number, Part, Sec, Year from remainder
    # Base number MUST start with a digit to avoid matching English words like 'is'
    # E.g. "302 (Part 2/Sec 16):2026" or "17424 (Part 1) : 2020" or "19901 : 2026" or "14644-2 : 2015"
    m_body = re.match(
        r'^(\d+[\w.-]*)'                             # base number (must start with digit, allows hyphens e.g. 14644-2, 60335-2-16)
        r'(?:\s*\(\s*Part\s*(\w+)'                   # optional Part (e.g. 2, 29)
        r'(?:\s*/\s*Sec(?:tion)?\s*(\w+))?\s*\))?'   # optional Section (e.g. 16, 2)
        r'(?:\s*:\s*(\d{4}))?'                       # optional year (e.g. 2026)
        r'\s*$',
        remainder,
        re.IGNORECASE
    )
    
    if not m_body:
        return None
        
    base = m_body.group(1)
    part = m_body.group(2)
    section = m_body.group(3)
    year = m_body.group(4)
    
    # Construct canonical designation
    designation_parts = [matched_family, f" {base}"]
    if part and section:
        designation_parts.append(f" (Part {part}/Sec {section})")
    elif part:
        designation_parts.append(f" (Part {part})")
        
    canonical_designation = "".join(designation_parts)
    if year:
        canonical_designation += f":{year}"
        
    return {
        "standard_designation": canonical_designation,
        "family": matched_family,
        "base_number": base,
        "part": part,
        "section": section,
        "year": year,
    }


def standard_number_to_preview_id_candidates(standard_number: str, publish_date: str | None = None) -> list[str]:
    """
    Generate an ordered list of candidate BSB Edge preview IDs for a given standard number.
    
    For plain IS standards:
        1. Primary: with year (e.g. 17424_2_2020, 302_2_16_2026)
        2. Fallback: without year (e.g. 17424_2, 302_2_16)
    
    For international-adoption families (IS/IEC/IEEE, IS/IEC, IS/ISO, etc.):
        Prefix-based candidates are generated first, then plain numeric.
        e.g. IS/IEC/IEEE 60079 (Part 30/Sec 2):2015 produces:
            iee60079_30_2_2015  (prefixed, with year)
            iee60079_30_2       (prefixed, without year)
            60079_30_2_2015     (plain, with year)
            60079_30_2          (plain, without year)
    
    Also generates alternative candidates from publish_date if it contains a different year.
    
    Returns an empty list for unrecognized formats.
    """
    identity = parse_standard_identity(standard_number)
    if not identity:
        return []
    
    base = identity["base_number"]
    # For preview ID, extract digits if base has hyphens or use cleaned base
    # In BIS BSB Edge, base IDs are generally digits: e.g. 302, 17424, 19901
    base_parts = [base]
    if identity["part"]:
        base_parts.append(identity["part"])
    if identity["section"]:
        base_parts.append(identity["section"])
    
    # Build plain (no-prefix) candidates
    plain_with_year = "_".join(base_parts + [identity["year"]]) if identity["year"] else None
    plain_without_year = "_".join(base_parts)
    
    # Check if this family has a BSB Edge prefix
    family = identity["family"]
    prefix = FAMILY_PREFIX_MAP.get(family, "")
    
    candidates = []
    
    if prefix:
        # Prefix candidates come first (higher priority)
        if plain_with_year:
            candidates.append(prefix + plain_with_year)       # e.g. iee60079_30_2_2015
            candidates.append(prefix + plain_without_year)    # e.g. iee60079_30_2
        else:
            candidates.append(prefix + plain_without_year)    # e.g. iee60079_30_2
    
    # Plain candidates as fallback
    if plain_with_year:
        candidates.append(plain_with_year)       # e.g. 60079_30_2_2015
        candidates.append(plain_without_year)    # e.g. 60079_30_2
    else:
        candidates.append(plain_without_year)    # e.g. 60079_30_2
    
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    candidates = deduped
        
    # Check if publish_date provides a different valid 4-digit year
    if publish_date:
        m = re.search(r'\b(19\d{2}|20\d{2})\b', str(publish_date))
        if m:
            pub_year = m.group(1)
            # Add both prefixed and plain publish-date alternatives
            alt_plain = "_".join(base_parts + [pub_year])
            alt_prefixed = prefix + alt_plain if prefix else None
            for alt_cand in [alt_prefixed, alt_plain]:
                if alt_cand and alt_cand not in candidates:
                    candidates.append(alt_cand)
    
    return candidates


def standard_number_to_preview_id(standard_number: str) -> str | None:
    """
    Convert a BIS standard number string to the primary BSB Edge preview ID.
    Returns None for unrecognized formats (logged for manual review).
    """
    candidates = standard_number_to_preview_id_candidates(standard_number)
    return candidates[0] if candidates else None


def get_preview_url(preview_id: str) -> str:
    """Get the full BSB Edge preview URL for a given preview ID."""
    return PREVIEW_URL_TEMPLATE.format(preview_id=preview_id)


def generate_preview_id_report(
    standards: list[dict],
    output_path: str | Path = "data/reports/preview_id_candidates.csv"
) -> Path:
    """
    Generate a dry-run report of all preview ID candidates.
    
    Writes a CSV with: standard_number, generated_preview_id, preview_url, status, warning
    Does NOT make any network requests.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    rows = []
    stats = {"ok": 0, "no_year": 0, "unrecognized": 0}
    
    for std in standards:
        original = std["original_standard_number"]
        preview_id = standard_number_to_preview_id(original)
        
        if preview_id:
            url = get_preview_url(preview_id)
            if std.get("year") is not None:
                status = "ok"
                warning = ""
                stats["ok"] += 1
            else:
                status = "warning"
                warning = "No year found — preview ID may be incomplete"
                stats["no_year"] += 1
        else:
            url = ""
            status = "unrecognized"
            warning = "Standard number format not recognized — needs manual review"
            stats["unrecognized"] += 1
        
        rows.append({
            "standard_number": original,
            "generated_preview_id": preview_id or "",
            "preview_url": url,
            "status": status,
            "warning": warning,
        })
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["standard_number", "generated_preview_id", "preview_url", "status", "warning"])
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(
        f"Preview ID report written to {output_path}: "
        f"{stats['ok']} ok, {stats['no_year']} no-year warnings, "
        f"{stats['unrecognized']} unrecognized"
    )
    
    return output_path
