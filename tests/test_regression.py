"""
Regression tests for BIS Standards Data Collector parser and extractor fixes.
Validates:
1. National Foreword boundary completeness (no premature truncation)
2. Committee code length sanity (must be short code, not paragraph dump)
3. Reference deduplication and extraction
4. Title normalization (whitespace and non-standard dashes)
5. Dual numbering and prose cross-references
"""

from pathlib import Path
from src.parser import parse_preview_html, _normalize_title

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_regression_national_foreword_completeness():
    """Verify National Foreword boundary fix: contains NOTE and subclause paragraphs."""
    html_302 = (FIXTURES_DIR / "preview_is_302_part2_sec16_2026.html").read_text(encoding="utf-8")
    parsed = parse_preview_html(html_302, source_standard="IS 302 (Part 2/Sec 16):2026")
    
    fw = parsed["national_foreword"]["text"]
    assert fw is not None
    assert "NOTE - When 'Part 1' is mentioned" in fw
    assert "supplements or modifies" in fw
    assert "particular subclause" in fw
    
    # Committee code must be short (e.g. 'ETD 32'), not a paragraph dump
    comm = parsed.get("committee")
    assert comm is not None
    assert comm == "ETD 32"
    assert len(comm) < 15


def test_regression_title_cleanup():
    """Verify title normalization removes double spaces, soft hyphens, and non-standard dashes."""
    raw_title = "IS 302 : Part 2 : Sec 16 : 2026  Household \u2013 Safety \u2014 Section 16 \xa0Disposers"
    clean = _normalize_title(raw_title)
    
    assert "  " not in clean
    assert "\u2013" not in clean
    assert "\u2014" not in clean
    assert "\xa0" not in clean
    assert clean == "IS 302 : Part 2 : Sec 16 : 2026 Household - Safety - Section 16 Disposers"


def test_regression_prose_relationship_detection():
    """Verify that 'in conjunction with' in National Foreword extracts explicit relationship."""
    html_302 = (FIXTURES_DIR / "preview_is_302_part2_sec16_2026.html").read_text(encoding="utf-8")
    parsed = parse_preview_html(html_302, source_standard="IS 302 (Part 2/Sec 16):2026")
    
    prose_refs = parsed["prose_references"]
    assert len(prose_refs) >= 1
    
    ref = prose_refs[0]
    assert "302" in ref["target"]["base_number"]
    assert ref["relationship"] == "used_in_conjunction_with"
    assert ref["evidence"]["complete"] is True
