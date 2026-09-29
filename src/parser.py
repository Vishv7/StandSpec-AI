"""
HTML parser for BSB Edge preview pages.
Phase 4 of the BIS Standards Data Collector — V1.2 Hardened.

Conforms to V1.2 Collector Data Contract:
- Multi-family reference parsing (IS, IS/IEC, IS/ISO, IS/ISO/IEC, ISO, IEC, ISO/IEC, ISO/IEC GUIDE, SP)
- Dual-numbered reference splitting (IS XXXX / ISO YYYY → dual_numbering, NOT equivalent_to)
- Continuation-row merging for multi-row reference table entries
- Structural reference evidence and title capture (html_table_row, html_paragraph)
- Semantic reference typing (BIS_STANDARD, INTERNATIONAL_STANDARD, INTERNATIONAL_GUIDE, BIS_SPECIAL_PUBLICATION)
- V1.2 relationship taxonomy (15 canonical types): normative_reference, test_method, terminology_reference,
  safety_reference, installation_reference, material_reference, measurement_method, calculation_method,
  dual_numbering, equivalent_to, used_in_conjunction_with, based_on, supersedes, superseded_by, related_to
- Explicit section presence vs absence vs fallback vs error tracking (Scope, Foreword, Notes)
- Inline NOTE extraction from any section (NOTE —, NOTE 1 —, etc.)
- Broader ICS extraction (p, td, span tags; multi-code; returns list)
- Committee false-positive prevention (rejects standard-number matches)
- Title separation: strips designation prefix, stores raw header_text separately
- Scope fallback labeling: status=fallback when derived from National Foreword
- Prose relationship extraction from National Foreword
"""

import re
import logging
from bs4 import BeautifulSoup, Tag
from src.preview_id import parse_standard_identity, KNOWN_FAMILIES

logger = logging.getLogger(__name__)

# ── V1.2 Relationship Taxonomy (15 canonical types) ──
# Rule: Only assign relationships when source evidence supports them.
# related_to is a DELIBERATE fallback, not a catch-all for unclassifiable relationships.
# dual_numbering is NEVER inferred as equivalent_to.
# The canonical field is "relationship"; "relationship_legacy" exists only for backwards compatibility.
CANONICAL_RELATIONSHIP_TYPES = frozenset([
    "normative_reference",
    "test_method",
    "terminology_reference",
    "safety_reference",
    "installation_reference",
    "material_reference",
    "measurement_method",
    "calculation_method",
    "dual_numbering",
    "equivalent_to",
    "used_in_conjunction_with",
    "based_on",
    "supersedes",
    "superseded_by",
    "related_to",
])
RELATIONSHIP_PHRASES = [
    # used_in_conjunction_with — ONLY for explicit conjunction language
    (r"in\s+conjunction\s+with", "used_in_conjunction_with"),
    (r"shall\s+be\s+read\s+(?:together\s+)?with", "used_in_conjunction_with"),
    (r"to\s+be\s+used\s+(?:together\s+)?with", "used_in_conjunction_with"),
    (r"to\s+be\s+read\s+(?:together\s+)?with", "used_in_conjunction_with"),
    # test_method — testing relationship
    (r"tested?\s+in\s+accordance\s+with", "test_method"),
    (r"test(?:ed|ing)?\s+(?:method|procedure)?\s*(?:as|in)\s+(?:per|accordance)", "test_method"),
    (r"test\s+as\s+per", "test_method"),
    (r"determined\s+as\s+per", "measurement_method"),
    (r"measured\s+(?:in\s+accordance\s+with|as\s+per)", "measurement_method"),
    (r"calculated\s+in\s+accordance\s+with", "calculation_method"),
    # material_reference
    (r"material\s+conforming\s+to", "material_reference"),
    (r"materials?\s+as\s+per", "material_reference"),
    # installation_reference
    (r"installed?\s+in\s+accordance\s+with", "installation_reference"),
    (r"installation\s+(?:as\s+per|in\s+accordance)", "installation_reference"),
    # safety_reference
    (r"safety\s+requirements?\s+of", "safety_reference"),
    (r"safety\s+(?:as\s+per|in\s+accordance)", "safety_reference"),
    # terminology
    (r"terms?\s+(?:and\s+)?definitions?\s+given\s+in", "terminology_reference"),
    (r"definitions?\s+as\s+given\s+in", "terminology_reference"),
    # general conformance — map to normative_reference, not used_in_conjunction_with
    (r"in\s+accordance\s+with", "normative_reference"),
    (r"complies?\s+with", "normative_reference"),
    # equivalence / adoption
    (r"is\s+identical\s+to", "equivalent_to"),
    (r"identical\s+under\s+dual\s+numbering\s+to", "equivalent_to"),
    (r"adopted\s+from", "based_on"),
    (r"based\s+on", "based_on"),
    # lifecycle
    (r"supplements?\s+or\s+modifies", "supersedes"),
    (r"supersedes", "supersedes"),
    (r"superseded\s+by", "superseded_by"),
]

# Pattern matching any reference standard starting with a recognized family
# Base number MUST start with a digit to avoid matching English words like 'is'
REFERENCE_PATTERN = re.compile(
    r'\b((?:IS/ISO/IEC|IS/IEC|IS/ISO|IS|ISO/IEC\s+GUIDE|ISO/IEC|ISO/TS|ISO|IEC|SP)\s+\d+[\w.-]*(?:\s*\((?:Part\s*\w+)(?:/Sec\s*\w+)?\))?(?:\s*:\s*\d{4})?)',
    re.IGNORECASE
)

# Pattern matching bare numeric standard designation in Indian Standards Section 2 (Normative References)
# BIS frequently omits the 'IS ' prefix for Indian Standards within Section 2 (e.g., '1070 : 1992', '1390 : 2019/ISO ...')
BARE_NUMERIC_STD_PATTERN = re.compile(
    r'^\s*(\d{3,6}(?:\s*\((?:Part\s*[\w\d]+)(?:\s*/\s*Sec(?:tion)?\s*[\w\d]+)?\))?\s*:\s*\d{4})'
)

# Pattern for scope-like sentences in National Foreword (fallback when no dedicated Scope section)
SCOPE_FALLBACK_PATTERNS = [
    r'This\s+standard\s+covers\b[^.]*\.',
    r'This\s+standard\s+specifies\b[^.]*\.',
    r'This\s+standard\s+(?:however\s+)?does\s+not\s+cover\b[^.]*\.',
    r'This\s+standard\s+establishes\b[^.]*\.',
    r'This\s+standard\s+provides\b[^.]*\.',
    r'This\s+standard\s+applies\s+to\b[^.]*\.',
    r'This\s+standard\s+is\s+applicable\s+to\b[^.]*\.',
]

# Inline NOTE pattern — matches NOTE, NOTE 1, NOTE 2 etc. followed by dash/em-dash/colon
INLINE_NOTE_PATTERN = re.compile(
    r'(NOTE\s*(?:\d+)?\s*[-—–:]\s*.+?)(?=\nNOTE\s|\n[A-Z]{2,}\s|\n\d+\.\s|\Z)',
    re.IGNORECASE | re.DOTALL
)


def classify_reference_semantic_type(family: str) -> str:
    """Classify the semantic family type of a standard."""
    fam_upper = family.upper()
    if fam_upper in ("IS", "IS/IEC", "IS/ISO", "IS/ISO/IEC"):
        return "BIS_STANDARD"
    elif fam_upper in ("ISO", "IEC", "ISO/IEC"):
        return "INTERNATIONAL_STANDARD"
    elif fam_upper == "ISO/IEC GUIDE":
        return "INTERNATIONAL_GUIDE"
    elif fam_upper == "SP":
        return "BIS_SPECIAL_PUBLICATION"
    return "OTHER"


def parse_reference_standard(raw_str: str) -> dict | None:
    """
    Parse a reference string into structured target components.
    
    Returns:
        {
            "designation": str,
            "family": str,
            "base_number": str,
            "part": str | None,
            "section": str | None,
            "year": str | None,
            "semantic_type": str,
            "display_number": str,
        }
    """
    ident = parse_standard_identity(raw_str)
    if not ident:
        return None
    
    semantic = classify_reference_semantic_type(ident["family"])
    
    # Clean display number (e.g. 'ISO 14644-2 : 2015')
    display_parts = [ident["family"], f" {ident['base_number']}"]
    if ident["part"] and ident["section"]:
        display_parts.append(f" (Part {ident['part']}/Sec {ident['section']})")
    elif ident["part"]:
        display_parts.append(f" (Part {ident['part']})")
    if ident["year"]:
        display_parts.append(f" : {ident['year']}")
    display_number = "".join(display_parts)
    
    return {
        "designation": ident["standard_designation"],
        "family": ident["family"],
        "base_number": ident["base_number"],
        "part": ident["part"],
        "section": ident["section"],
        "year": ident["year"],
        "semantic_type": semantic,
        "display_number": display_number,
    }


def parse_preview_html(html: str, source_standard: str = None) -> dict:
    """
    Parse a BSB Edge preview HTML page according to the V1.2 Data Contract.
    
    Returns structured content dictionary with:
        header_text, title, ics_codes, committee,
        scope: {text, status, extraction_method, scope_source_section},
        national_foreword: {text, status, extraction_method},
        notes: {items: [{text, evidence, extraction_method}], status, extraction_method},
        formal_references: list[dict],
        prose_references: list[dict],
        parse_warnings: list[str]
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.body if soup.body else soup
    
    warnings = []
    
    # 1. Header fields — A6: separate title from header_text
    raw_header = _extract_raw_header(body)
    title = _extract_title_from_header(raw_header)
    ics_raw, ics_codes = _extract_ics_codes(body)  # A3/P3: returns (raw_string, list)
    committee = _extract_committee(body)  # A4: fixed false positives
    
    # 2. Sequential sections extraction
    sections = _extract_sections_sequential(body)
    
    # 3. Scope — A7: proper fallback labeling
    scope_text = _clean_text(sections.get("scope"))
    scope_method = "html_section" if scope_text else None
    scope_source_section = "SCOPE" if scope_text else None
    
    # 4. National Foreword
    foreword_text = _clean_text(sections.get("national_foreword"))
    foreword_method = "html_section" if foreword_text else None
    
    # Fallback scope from National Foreword if dedicated Scope is absent
    if not scope_text and foreword_text:
        fallback_scope = _extract_scope_from_foreword(foreword_text)
        if fallback_scope:
            scope_text = fallback_scope
            scope_method = "national_foreword_fallback"
            scope_source_section = "NATIONAL_FOREWORD"
            
    # A7: status is "fallback" when derived from foreword, not "present"
    if scope_method == "national_foreword_fallback":
        scope_status = "fallback"
    elif scope_text:
        scope_status = "present"
    else:
        scope_status = "absent"
    foreword_status = "present" if foreword_text else "absent"
    
    # 5. Notes — A5: inline NOTE extraction from full page body
    notes_items = []
    
    # First try dedicated NOTES section
    notes_raw = sections.get("notes")
    if notes_raw:
        extracted_notes = _extract_notes(notes_raw)
        for n in extracted_notes:
            notes_items.append({
                "text": n,
                "evidence": n,
                "extraction_method": "html_section"
            })
    
    # A5: Also scan full body text for inline NOTEs
    full_text = body.get_text(separator='\n', strip=True)
    inline_notes = _extract_inline_notes(full_text)
    existing_note_texts = {item["text"] for item in notes_items}
    for note in inline_notes:
        if note not in existing_note_texts:
            notes_items.append({
                "text": note,
                "evidence": note,
                "extraction_method": "inline_note"
            })
    
    notes_status = "present" if notes_items else "absent"
    notes_method = "html_section" if notes_raw else ("inline_note" if notes_items else None)
    
    # 6. Formal references from References section (A1: dual-numbered, A2: continuation rows)
    formal_refs = []
    ref_sec_text = sections.get("references", "")
    has_ref_heading = bool(ref_sec_text) or bool(soup.find(lambda tag: tag.name in ('b', 'strong', 'p') and 'REFERENCES' in tag.get_text().upper()))
    if has_ref_heading:
        formal_refs = _extract_formal_references_structural(soup, ref_sec_text, source_standard)
        
    # Classify references status explicitly to distinguish absence from deferred Annex references
    if formal_refs:
        references_status = "parsed"
    elif re.search(r'Annex[\s-]*A|in\s+Annex', ref_sec_text, re.IGNORECASE):
        references_status = "referenced_in_annex_not_in_preview"
    elif has_ref_heading and len(ref_sec_text.strip()) < 40:
        references_status = "truncated_or_empty_in_preview"
    elif has_ref_heading:
        references_status = "none_found"
    else:
        references_status = "absent"

    # 7. Prose references from National Foreword (A13: V1.2 taxonomy)
    prose_refs = []
    if foreword_text:
        prose_refs = _extract_prose_references(foreword_text, source_standard)
        
    return {
        "header_text": raw_header,
        "title": title,
        "title_source": "preview" if title else "excel",
        "ics_raw": ics_raw,  # P3: exact BIS source string
        "ics_codes": ics_codes,  # A3: list of ICS codes, preserved exactly
        "ics_code": ics_codes[0] if ics_codes else None,  # backwards compat
        "committee": committee,
        "scope": {
            "text": scope_text,
            "status": scope_status,
            "extraction_method": scope_method,
            "scope_source_section": scope_source_section,  # A7
        },
        "national_foreword": {
            "text": foreword_text,
            "status": foreword_status,
            "extraction_method": foreword_method,
        },
        "notes": {
            "items": notes_items,
            "status": notes_status,
            "extraction_method": notes_method,
        },
        "formal_references": formal_refs,
        "references_status": references_status,
        "prose_references": prose_refs,
        "parse_warnings": warnings,
    }


def _extract_sections_sequential(body) -> dict[str, str]:
    """
    Extract sections by scanning text lines for section heading boundaries.
    Handles dotted headings (e.g. '1. SCOPE', '2. REFERENCES').
    """
    full_text = body.get_text(separator='\n', strip=True)
    
    patterns = [
        ('national_foreword', re.compile(r'^\s*NATIONAL\s+FOREWORD\s*$', re.IGNORECASE)),
        ('scope', re.compile(r'^\s*1\.?\s+SCOPE\s*$|^\s*SCOPE\s*$', re.IGNORECASE)),
        ('references', re.compile(r'^\s*2\.?\s+(?:NORMATIVE\s+)?REFERENCES\s*$|^\s*(?:NORMATIVE\s+)?REFERENCES\s*$', re.IGNORECASE)),
        ('notes', re.compile(r'^\s*NOTES\s*$', re.IGNORECASE)),
        ('foreword', re.compile(r'^\s*FOREWORD\s*$', re.IGNORECASE)),
    ]
    
    lines = full_text.splitlines()
    sections = {}
    current_sec = None
    current_lines = []
    
    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue
            
        matched_sec = None
        for sec_name, pat in patterns:
            if pat.match(line_s):
                matched_sec = sec_name
                break
                
        if matched_sec:
            if current_sec and current_lines:
                sections[current_sec] = '\n'.join(current_lines).strip()
            current_sec = matched_sec
            current_lines = []
        elif current_sec:
            current_lines.append(line_s)
            
    if current_sec and current_lines:
        sections[current_sec] = '\n'.join(current_lines).strip()
        
    return sections


def _extract_formal_references_structural(soup: BeautifulSoup, section_text: str, source_standard: str = None) -> list[dict]:
    """
    Extract formal references with structural evidence (html_table_row or html_paragraph).
    
    P1: Continuation state machine tracks current_base and current_part separately.
    P2: Dual-numbered splitting via _split_dual_numbered() returns structured results.
    
    State machine rules:
    - Row with complete IS/ISO/SP designation: reset state (current_base, current_part)
    - Row starting with (Part X/Sec Y): merge with current_base
    - Row starting with (Part X): merge with current_base, update current_part
    - Row starting with (Sec Y): merge with current_base + current_part
    """
    refs_by_designation = {}
    
    # Strategy A: Check for HTML table in the references section
    ref_heading = soup.find(lambda tag: tag.name in ('p', 'b', 'strong', 'td', 'h1', 'h2', 'h3', 'h4') and 
                            re.search(r'\b(?:NORMATIVE\s+)?REFERENCES\b', tag.get_text(), re.IGNORECASE))
    
    tables_to_check = []
    if ref_heading:
        parent = ref_heading.find_parent('div') or soup
        tables_to_check = parent.find_all('table')
    if not tables_to_check:
        tables_to_check = soup.find_all('table')
        
    found_table_refs = False
    for table_idx, table in enumerate(tables_to_check):
        rows = table.find_all('tr')
        if not rows:
            continue
        
        # P1: Continuation state — track base and part separately
        current_base = None    # e.g. "IS 5887"
        current_part = None    # e.g. "Part 8" (for sub-section continuation)
            
        for row_idx, tr in enumerate(rows):
            tds = tr.find_all(['td', 'th'])
            if len(tds) < 2:
                continue
            
            col0_text = tds[0].get_text(strip=True)
            col1_text = tds[1].get_text(strip=True)
            
            # Check for header row
            if "IS No" in col0_text or ("Standard" in col0_text and "Title" in col1_text):
                continue
            
            # P1: Determine if this is a continuation row
            is_continuation = False
            merged_text = col0_text
            
            # Case 1: Row starts with (Part X/Sec Y) — merge with current_base
            m_part_sec = re.match(r'^\s*\(\s*Part\s+(\w+)\s*/\s*Sec(?:tion)?\s+(\w+)\s*\)', col0_text)
            if m_part_sec and current_base:
                part_val = m_part_sec.group(1)
                sec_val = m_part_sec.group(2)
                # Extract remaining text after the Part/Sec declaration (year, dual-number)
                remainder = col0_text[m_part_sec.end():]
                merged_text = f"{current_base} (Part {part_val}/Sec {sec_val}){remainder}"
                current_part = f"Part {part_val}"
                is_continuation = True
            
            # Case 2: Row starts with (Part X) — merge with current_base, update current_part
            elif re.match(r'^\s*\(\s*Part\s+\w+', col0_text) and current_base:
                m_part = re.match(r'^\s*(\(\s*Part\s+\w+\s*\))', col0_text)
                if m_part:
                    part_text = m_part.group(1)
                    remainder = col0_text[m_part.end():]
                    merged_text = f"{current_base} {part_text}{remainder}"
                    # Extract part value for sub-section tracking
                    pm = re.search(r'Part\s+(\w+)', part_text)
                    if pm:
                        current_part = f"Part {pm.group(1)}"
                    is_continuation = True
            
            # Case 3: Row starts with (Sec Y) — merge with current_base + current_part
            elif re.match(r'^\s*\(\s*Sec(?:tion)?\s+\w+', col0_text) and current_base and current_part:
                m_sec = re.match(r'^\s*(\(\s*Sec(?:tion)?\s+\w+\s*\))', col0_text)
                if m_sec:
                    sec_text = m_sec.group(1)
                    remainder = col0_text[m_sec.end():]
                    # Merge: IS 5887 (Part 8/Sec 1) : 2023/ISO ...
                    part_num = re.search(r'Part\s+(\w+)', current_part)
                    sec_num = re.search(r'Sec(?:tion)?\s+(\w+)', sec_text)
                    if part_num and sec_num:
                        merged_text = f"{current_base} (Part {part_num.group(1)}/Sec {sec_num.group(1)}){remainder}"
                    else:
                        merged_text = f"{current_base} {current_part} {sec_text}{remainder}"
                    is_continuation = True
            
            if not is_continuation:
                # Check if this row is a complete standard designation — reset state
                complete_match = re.match(r'^((?:IS/ISO/IEC|IS/IEC|IS/ISO|IS|ISO/IEC\s+GUIDE|ISO/IEC|ISO|IEC|SP)\s+\d+)', col0_text, re.IGNORECASE)
                if complete_match:
                    current_base = complete_match.group(1).strip()
                    current_part = None  # Reset part tracking
                else:
                    # Not a recognizable standard or continuation — skip but don't reset
                    pass
            
            # P2: Split dual-numbered standards and process
            dual_result = _split_dual_numbered(merged_text)
            
            primary_parsed = None
            for i, entry in enumerate(dual_result):
                parsed_std = parse_reference_standard(entry["text"])
                if not parsed_std:
                    continue
                
                found_table_refs = True
                desig = parsed_std["designation"]
                evidence_text = f"{col0_text} {col1_text}".strip()
                
                # Determine relationship — use canonical taxonomy
                if entry["is_dual"] and i == 0:
                    primary_parsed = parsed_std
                    relationship = "normative_reference"
                elif entry["is_dual"] and i > 0 and primary_parsed:
                    relationship = "dual_numbering"
                else:
                    relationship = "normative_reference"
                
                refs_by_designation[desig] = {
                    "source_standard": source_standard,
                    "target": {
                        "designation": desig,
                        "family": parsed_std["family"],
                        "base_number": parsed_std["base_number"],
                        "part": parsed_std["part"],
                        "section": parsed_std["section"],
                        "year": parsed_std["year"],
                    },
                    "title": col1_text if col1_text and relationship != "dual_numbering" else None,
                    "reference_type": "formal_reference",
                    "relationship": relationship,
                    "relationship_confidence": "structural",
                    "section": "REFERENCES",
                    "evidence": {
                        "text": evidence_text,
                        "source_section": "REFERENCES",
                        "extraction_method": "html_table_row",
                        "complete": True,
                        "continuation_resolved": is_continuation,
                        "table_index": table_idx,
                        "row_index": row_idx,
                        "column_name": "IS No / Title",
                        "sentence_text": None,
                    },
                    "linked_standard": primary_parsed["designation"] if (entry["is_dual"] and i > 0 and primary_parsed) else None,
                    "dual_numbering_raw": entry.get("raw") if entry["is_dual"] else None,
                    # Backwards compatibility fields (legacy — use "relationship" as canonical)
                    "target_is": desig,
                    "target_year": parsed_std["year"],
                    "relationship_legacy": relationship,
                    "confidence": "stated",
                    "source_section": "References",
                }
                
    if found_table_refs:
        return list(refs_by_designation.values())
        
    # Strategy B: Paragraph/line scanning from section_text
    if section_text:
        current_base = None
        current_part = None
        lines = section_text.splitlines()
        for line in lines:
            line_s = line.strip()
            if not line_s:
                continue
            
            # Continuation row handling in paragraph mode
            is_continuation = False
            merged_text = line_s
            
            m_part_sec = re.match(r'^\s*\(\s*Part\s+(\w+)\s*/\s*Sec(?:tion)?\s+(\w+)\s*\)', line_s)
            if m_part_sec and current_base:
                part_val = m_part_sec.group(1)
                sec_val = m_part_sec.group(2)
                remainder = line_s[m_part_sec.end():]
                merged_text = f"{current_base} (Part {part_val}/Sec {sec_val}){remainder}"
                current_part = f"Part {part_val}"
                is_continuation = True
            elif re.match(r'^\s*\(\s*Part\s+\w+', line_s) and current_base:
                m_part = re.match(r'^\s*(\(\s*Part\s+\w+\s*\))', line_s)
                if m_part:
                    part_text = m_part.group(1)
                    remainder = line_s[m_part.end():]
                    merged_text = f"{current_base} {part_text}{remainder}"
                    pm = re.search(r'Part\s+(\w+)', part_text)
                    if pm:
                        current_part = f"Part {pm.group(1)}"
                    is_continuation = True
            elif re.match(r'^\s*\(\s*Sec(?:tion)?\s+\w+', line_s) and current_base and current_part:
                m_sec = re.match(r'^\s*(\(\s*Sec(?:tion)?\s+\w+\s*\))', line_s)
                if m_sec:
                    sec_text = m_sec.group(1)
                    remainder = line_s[m_sec.end():]
                    part_num = re.search(r'Part\s+(\w+)', current_part)
                    sec_num = re.search(r'Sec(?:tion)?\s+(\w+)', sec_text)
                    if part_num and sec_num:
                        merged_text = f"{current_base} (Part {part_num.group(1)}/Sec {sec_num.group(1)}){remainder}"
                    is_continuation = True
            
            # Check for bare numeric standard in Section 2 (Indian Standards omit 'IS' prefix)
            effective_line = line_s
            is_bare_std = False
            if not is_continuation and BARE_NUMERIC_STD_PATTERN.match(line_s):
                effective_line = f"IS {line_s}"
                merged_text = effective_line
                is_bare_std = True

            if not is_continuation:
                complete_match = re.match(r'^((?:IS/ISO/IEC|IS/IEC|IS/ISO|IS|ISO/IEC\s+GUIDE|ISO/IEC|ISO|IEC|SP)\s+\d+)', effective_line, re.IGNORECASE)
                if complete_match:
                    current_base = complete_match.group(1).strip()
                    current_part = None
            
            # Split dual-numbered and extract
            dual_result = _split_dual_numbered(merged_text)
            
            primary_parsed = None
            for i, entry in enumerate(dual_result):
                matches = REFERENCE_PATTERN.findall(entry["text"])
                for raw_match in matches:
                    parsed_std = parse_reference_standard(raw_match)
                    if not parsed_std:
                        continue
                        
                    desig = parsed_std["designation"]
                    target_line_for_title = effective_line if is_bare_std else line_s
                    title = target_line_for_title.replace(raw_match, "").strip(" -:\t") or None
                    
                    if entry["is_dual"] and i == 0:
                        primary_parsed = parsed_std
                        relationship = "normative_reference"
                    elif entry["is_dual"] and i > 0 and primary_parsed:
                        relationship = "dual_numbering"
                    else:
                        relationship = "normative_reference"
                    
                    if desig not in refs_by_designation:
                        refs_by_designation[desig] = {
                            "source_standard": source_standard,
                            "target": {
                                "designation": desig,
                                "family": parsed_std["family"],
                                "base_number": parsed_std["base_number"],
                                "part": parsed_std["part"],
                                "section": parsed_std["section"],
                                "year": parsed_std["year"],
                            },
                            "title": title if relationship != "dual_numbering" else None,
                            "reference_type": "formal_reference",
                            "relationship": relationship,
                            "relationship_confidence": "structural",
                            "section": "REFERENCES",
                            "evidence": {
                                "text": line_s,
                                "source_section": "REFERENCES",
                                "extraction_method": "html_paragraph",
                                "complete": True,
                                "continuation_resolved": is_continuation,
                                "bare_number_resolved": is_bare_std,
                                "table_index": None,
                                "row_index": None,
                                "column_name": None,
                                "sentence_text": None,
                            },
                            "linked_standard": primary_parsed["designation"] if (entry["is_dual"] and i > 0 and primary_parsed) else None,
                            "dual_numbering_raw": entry.get("raw") if entry["is_dual"] else None,
                            "target_is": desig,
                            "target_year": parsed_std["year"],
                            "relationship_legacy": relationship,
                            "confidence": "stated",
                            "source_section": "References",
                        }
                    
    return list(refs_by_designation.values())


def _split_dual_numbered(text: str) -> list[dict]:
    """
    P2: Split dual-numbered standards. Returns structured results.
    
    Handles:
    - 'IS 18319 : 2024 / ISO 17665 : 2024'  (space around /)
    - 'IS 2828 : 2019/ISO 472 : 2013'        (no space around /)
    - 'IS 5402 (Part 1) : 2021/ISO 4833-1 : 2013'  (part + no space)
    
    Only splits when both sides look like standard designations.
    
    Returns list of dicts:
    [
        {"text": "IS 2828 : 2019", "is_dual": True, "raw": "IS 2828 : 2019/ISO 472 : 2013"},
        {"text": "ISO 472 : 2013", "is_dual": True, "raw": "IS 2828 : 2019/ISO 472 : 2013"},
    ]
    """
    raw = text
    
    # Try splitting on / where it separates two standard designations
    # Pattern: ... FAMILY1 NUMBER1 ... / FAMILY2 NUMBER2 ...
    # Look for /ISO, /IEC, /SP followed by a space and digit (international counterpart)
    split_match = re.search(
        r'/(ISO/IEC\s+GUIDE|ISO/IEC|ISO/TS|ISO|IEC|SP)\s+(\d+)',
        text
    )
    
    if split_match:
        split_pos = split_match.start()
        part1 = text[:split_pos].strip()
        part2 = text[split_pos + 1:].strip()  # Skip the /
        
        # Verify part1 looks like a standard
        if parse_reference_standard(part1):
            return [
                {"text": part1, "is_dual": True, "raw": raw},
                {"text": part2, "is_dual": True, "raw": raw},
            ]
    
    # Also try ' / ' explicit separator
    if ' / ' in text:
        parts = text.split(' / ', 1)
        if parse_reference_standard(parts[0].strip()):
            return [
                {"text": parts[0].strip(), "is_dual": True, "raw": raw},
                {"text": parts[1].strip(), "is_dual": True, "raw": raw},
            ]
    
    return [{"text": text, "is_dual": False, "raw": raw}]


def _extract_prose_references(foreword_text: str, source_standard: str = None) -> list[dict]:
    """
    Scan prose text (National Foreword) for relationship phrases and extract references.
    A13: Uses V1.2 taxonomy with 15 canonical relationship types.
    E.g. "This standard is to be used in conjunction with IS 302 (Part 1) : 2024."
    """
    prose_refs = {}
    
    for phrase_pat, rel_type in RELATIONSHIP_PHRASES:
        for phrase_match in re.finditer(phrase_pat, foreword_text, re.IGNORECASE):
            # Look forward for standard mention
            context_start = max(0, phrase_match.start() - 30)
            context_end = min(len(foreword_text), phrase_match.end() + 250)
            context = foreword_text[context_start:context_end]
            
            matches = REFERENCE_PATTERN.findall(context)
            for raw_match in matches:
                parsed_std = parse_reference_standard(raw_match)
                if not parsed_std:
                    continue
                    
                desig = parsed_std["designation"]
                key = (desig, rel_type)
                
                sentence = _extract_evidence_sentence(foreword_text, phrase_match.start(), raw_match)
                
                if key not in prose_refs or len(sentence) > len(prose_refs[key]["evidence"]["text"]):
                    prose_refs[key] = {
                        "source_standard": source_standard,
                        "target": {
                            "designation": desig,
                            "family": parsed_std["family"],
                            "base_number": parsed_std["base_number"],
                            "part": parsed_std["part"],
                            "section": parsed_std["section"],
                            "year": parsed_std["year"],
                        },
                        "title": None,
                        "reference_type": "prose_reference",
                        "relationship": rel_type,
                        "relationship_confidence": "explicit_prose",
                        "section": "NATIONAL FOREWORD",
                        "evidence": {
                            "text": sentence,
                            "source_section": "NATIONAL FOREWORD",
                            "extraction_method": "html_paragraph",
                            "complete": True,
                            "continuation_resolved": False,
                            "table_index": None,
                            "row_index": None,
                            "column_name": None,
                            "sentence_text": sentence,
                        },
                        "linked_standard": None,
                        # Backwards compatibility fields (legacy — use "relationship" as canonical)
                        "target_is": desig,
                        "target_year": parsed_std["year"],
                        "relationship_legacy": rel_type,
                        "confidence": "inferred",
                        "source_section": "National Foreword",
                    }
                    
    return list(prose_refs.values())


def _extract_evidence_sentence(text: str, phrase_start: int, target_raw: str) -> str:
    """Extract the sentence containing the relationship phrase verbatim."""
    start = phrase_start
    while start > 0 and text[start - 1] not in '.\n':
        start -= 1
        
    target_pos = text.find(target_raw, phrase_start)
    if target_pos >= 0:
        end = target_pos + len(target_raw)
    else:
        end = phrase_start + 60
        
    while end < len(text) and text[end] not in '.\n':
        end += 1
    if end < len(text) and text[end] == '.':
        end += 1
        
    return text[start:end].strip()


def _extract_raw_header(body) -> str | None:
    """
    Extract the raw header text containing the standard designation and title.
    Searches across p, b, strong, h1, h2, h3, span tags near the top of the body.
    """
    for el in body.find_all(['p', 'b', 'strong', 'h1', 'h2', 'h3', 'span']):
        text = el.get_text(strip=True)
        if text and 10 < len(text) < 400:
            for fam in KNOWN_FAMILIES:
                if re.search(r'\b' + re.escape(fam) + r'\s+\d+', text, re.IGNORECASE):
                    return _normalize_title(text)
    return None


def _extract_title_from_header(raw_header: str) -> str | None:
    """
    A6: Extract clean title by stripping the standard designation prefix from header.
    E.g. 'IS 19901 : 2026 Safe Handling of Biotherapeutic Products' -> 'Safe Handling of Biotherapeutic Products'
    """
    if not raw_header:
        return None
    
    # Try to strip the designation prefix
    # Pattern: FAMILY BASE [(Part X[/Sec Y])] [: YEAR]
    stripped = re.sub(
        r'^(?:IS/ISO/IEC|IS/IEC|IS/ISO|IS|ISO/IEC\s+GUIDE|ISO/IEC|ISO|IEC|SP)'
        r'\s+\d+[\w.-]*'
        r'(?:\s*\(\s*Part\s*\w+(?:\s*/\s*Sec(?:tion)?\s*\w+)?\s*\))?'
        r'(?:\s*:\s*\d{4})?'
        r'\s*[-—–]?\s*',
        '', raw_header, flags=re.IGNORECASE
    ).strip()
    
    return stripped if stripped and len(stripped) > 3 else raw_header


def _extract_ics_codes(body) -> tuple[str | None, list[str]]:
    """
    A3/P3: Extract ICS codes from multiple HTML element types.
    Returns (ics_raw, ics_codes):
        ics_raw: the exact BIS source string (e.g., "ICS 01.040.11; 111.020.99")
        ics_codes: list of individual ICS code strings, preserved exactly as BIS displays
    
    IMPORTANT: Do NOT normalize values. 01.04.11 != 01.040.11 from the collector's perspective.
    """
    ics_raw = None
    ics_list = []
    
    # Search across p, td, span, div tags
    for el in body.find_all(['p', 'td', 'span', 'div']):
        text = el.get_text(strip=True)
        if not text:
            continue
        
        # Match "ICS" followed by dotted numeric codes
        m = re.match(r'^(ICS\s+[\d.,;\s]+)$', text, re.IGNORECASE)
        if m:
            ics_raw = m.group(1).strip()
            raw_codes = re.sub(r'^ICS\s+', '', ics_raw, flags=re.IGNORECASE)
            # Split on comma or semicolon for multi-code values
            for code in re.split(r'[,;]\s*', raw_codes):
                code = code.strip()
                if code and re.match(r'^\d+\.\d+', code):
                    if code not in ics_list:
                        ics_list.append(code)
            continue
        
        # Also try embedded ICS in longer text (e.g. header paragraphs)
        m_embedded = re.search(r'(ICS\s+(?:\d+\.\d+[\d.]*(?:\s*[,;]\s*\d+\.\d+[\d.]*)*))', text, re.IGNORECASE)
        if m_embedded and len(text) < 200:
            if not ics_raw:
                ics_raw = m_embedded.group(1).strip()
            raw_codes = re.sub(r'^ICS\s+', '', m_embedded.group(1), flags=re.IGNORECASE)
            for code in re.split(r'[,;]\s*', raw_codes):
                code = code.strip()
                if code and re.match(r'^\d+\.\d+', code):
                    if code not in ics_list:
                        ics_list.append(code)
    
    return ics_raw, ics_list


def _extract_committee(body) -> str | None:
    """
    A4: Extract technical committee short code (e.g., 'ETD 32', 'AYD 07', 'AYD04').
    Fixed: accepts 'AYD04', 'AYD-04', 'ETD 32', 'ETD-32' patterns.
    Fixed: rejects anything that looks like a standard number to prevent false positives.
    """
    found_ics = False
    for p in body.find_all(['p', 'td']):
        text = p.get_text(strip=True)
        if not text:
            continue
        if re.match(r'^ICS\s+', text):
            found_ics = True
            continue
        if found_ics:
            # Accept committee codes: 2-5 uppercase letters followed by digits
            # with optional space, hyphen, or no separator
            if re.match(r'^[A-Z]{2,5}[\s-]?\d{1,3}\b', text) and len(text) < 40:
                # A4: Reject if it looks like a standard number
                # Standard numbers have family prefix followed by large base number (typically 3+ digits)
                if re.match(r'^(?:IS|SP|ISO|IEC)\s+\d{3,}', text, re.IGNORECASE):
                    continue
                return text.strip()
            if "FOREWORD" in text.upper():
                break
    return None


def _extract_scope_from_foreword(foreword_text: str) -> str | None:
    """Fallback: extract scope-like sentences from National Foreword."""
    scope_sentences = []
    for pattern in SCOPE_FALLBACK_PATTERNS:
        matches = re.findall(pattern, foreword_text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            s = match.strip()
            if s and s not in scope_sentences:
                scope_sentences.append(s)
    return " ".join(scope_sentences) if scope_sentences else None


def _extract_notes(notes_text: str) -> list[str]:
    """Extract individual notes from the notes section."""
    notes = []
    parts = re.split(r'\n(?=\d+\s+)', notes_text)
    for part in parts:
        cleaned = part.strip()
        if cleaned and len(cleaned) > 3:
            notes.append(cleaned)
    if not notes and notes_text.strip():
        notes = [notes_text.strip()]
    return notes


def _extract_inline_notes(full_text: str) -> list[str]:
    """
    A5: Extract inline NOTE patterns from full page body text.
    Matches: NOTE — ..., NOTE 1 — ..., NOTE 2 — ..., NOTE: ...
    """
    notes = []
    # Split on line boundaries and find NOTE lines
    for m in re.finditer(r'(?:^|\n)\s*(NOTE\s*(?:\d+)?\s*[-—–:]\s*.+?)(?=\n\s*NOTE\s|\n\s*\d+\.?\s+[A-Z]|\n\s*[A-Z]{3,}\s|\Z)', full_text, re.IGNORECASE | re.DOTALL):
        note_text = m.group(1).strip()
        if note_text and len(note_text) > 10:
            # Clean up: collapse internal whitespace but preserve meaning
            note_text = re.sub(r'\s+', ' ', note_text)
            notes.append(note_text)
    return notes


def _normalize_title(title: str) -> str:
    """Normalize a title string: collapse whitespace and dashes."""
    if not title:
        return title
    title = re.sub(r'\s+', ' ', title).strip()
    title = title.replace('\u2013', '-').replace('\u2014', '-').replace('\u2015', '-')
    title = title.replace('\u00ad', '').replace('\xa0', ' ')
    return title


def _clean_text(text: str) -> str | None:
    """Clean text by normalizing whitespace within paragraphs."""
    if not text:
        return None
    text = text.replace('\xa0', ' ')
    lines = [re.sub(r'  +', ' ', line).strip() for line in text.split('\n')]
    cleaned = '\n'.join([l for l in lines if l])
    return cleaned if cleaned else None
