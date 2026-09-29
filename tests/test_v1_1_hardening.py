"""
Comprehensive automated tests for SIH DATA COLLECTOR V1.1 Hardening Pass.
Validates all Frozen V1.1 Data Contract requirements using clean, self-contained fixtures.
Requires zero external network access and zero dependence on operational caches.
"""

import json
from pathlib import Path
import pytest
from openpyxl import Workbook

from src.preview_id import (
    parse_standard_identity,
    standard_number_to_preview_id,
    standard_number_to_preview_id_candidates,
)
from src.parser import (
    parse_preview_html,
    parse_reference_standard,
    classify_reference_semantic_type,
)
from src.fetcher import PreviewFetcher
from src.collector import Collector

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ── 1. Canonical Identity & Preview ID Generation Tests ──

def test_canonical_identity_confirmed_mappings():
    """Verify canonical identity parsing on confirmed standard numbers."""
    cases = [
        ("IS 19901:2026", "IS", "19901", None, None, "2026", "IS 19901:2026"),
        ("IS 17874 (Part 2):2026", "IS", "17874", "2", None, "2026", "IS 17874 (Part 2):2026"),
        ("IS 302 (Part 2/Sec 16):2026", "IS", "302", "2", "16", "2026", "IS 302 (Part 2/Sec 16):2026"),
        ("IS/IEC 60079 (Part 29/Sec 2):2015", "IS/IEC", "60079", "29", "2", "2015", "IS/IEC 60079 (Part 29/Sec 2):2015"),
        ("SP 45:1988", "SP", "45", None, None, "1988", "SP 45:1988"),
    ]
    for raw, fam, base, part, sec, year, expected_desig in cases:
        ident = parse_standard_identity(raw)
        assert ident is not None, f"Failed to parse identity for '{raw}'"
        assert ident["family"] == fam
        assert ident["base_number"] == base
        assert ident["part"] == part
        assert ident["section"] == sec
        assert ident["year"] == year
        assert ident["standard_designation"] == expected_desig


def test_preview_id_candidates():
    """Verify primary and fallback candidate ID generation."""
    # Standard with year: primary with year, fallback without year
    cands_19901 = standard_number_to_preview_id_candidates("IS 19901:2026")
    assert cands_19901 == ["19901_2026", "19901"]

    cands_part = standard_number_to_preview_id_candidates("IS 17424 (Part 1):2020")
    assert cands_part == ["17424_1_2020", "17424_1"]

    cands_sec = standard_number_to_preview_id_candidates("IS 302 (Part 2/Sec 16):2026")
    assert cands_sec == ["302_2_16_2026", "302_2_16"]

    # Primary generator matches exit criteria
    assert standard_number_to_preview_id("IS 19901:2026") == "19901_2026"
    assert standard_number_to_preview_id("IS 19897:2026") == "19897_2026"
    assert standard_number_to_preview_id("IS 17874 (Part 2):2026") == "17874_2_2026"
    assert standard_number_to_preview_id("IS 302 (Part 2/Sec 16):2026") == "302_2_16_2026"


# ── 2. Reference Parsing & Multi-Family Recognition Tests ──

def test_parse_reference_standard_families():
    """Verify recognition and semantic typing across all required reference families."""
    cases = [
        ("IS 18926 : 2024", "IS", "18926", "2024", "BIS_STANDARD"),
        ("IS/IEC 61439 : 2020", "IS/IEC", "61439", "2020", "BIS_STANDARD"),
        ("IS/ISO/IEC 22237-3 : 2021", "IS/ISO/IEC", "22237-3", "2021", "BIS_STANDARD"),
        ("ISO 14644-2 : 2015", "ISO", "14644-2", "2015", "INTERNATIONAL_STANDARD"),
        ("IEC 60335-1 : 2020", "IEC", "60335-1", "2020", "INTERNATIONAL_STANDARD"),
        ("ISO/IEC GUIDE 51 : 2014", "ISO/IEC GUIDE", "51", "2014", "INTERNATIONAL_GUIDE"),
        ("SP 45 : 1988", "SP", "45", "1988", "BIS_SPECIAL_PUBLICATION"),
    ]
    for raw, fam, base, year, semantic in cases:
        parsed = parse_reference_standard(raw)
        assert parsed is not None, f"Failed to parse reference: {raw}"
        assert parsed["family"] == fam
        assert parsed["base_number"] == base
        assert parsed["year"] == year
        assert parsed["semantic_type"] == semantic


def test_reference_extraction_from_html_table():
    """Verify that formal references and full titles are structurally extracted from HTML tables."""
    html_path = FIXTURES_DIR / "preview_is_19901_2026.html"
    html = html_path.read_text(encoding="utf-8")
    
    parsed = parse_preview_html(html, source_standard="IS 19901:2026")
    formal_refs = parsed["formal_references"]
    
    # Must extract both IS and ISO references
    assert len(formal_refs) == 5
    
    # Check ISO reference presence
    iso_ref = next((r for r in formal_refs if r["target"]["family"] == "ISO"), None)
    assert iso_ref is not None, "ISO 14644-2 reference was not extracted!"
    assert iso_ref["target"]["designation"] == "ISO 14644-2:2015"
    assert iso_ref["reference_type"] == "formal_reference"
    assert iso_ref["relationship"] == "normative_reference"
    assert iso_ref["evidence"]["extraction_method"] == "html_table_row"
    assert iso_ref["evidence"]["complete"] is True
    assert "Cleanrooms and associated controlled environments" in iso_ref["title"]
    assert "ISO 14644-2 : 2015 Cleanrooms" in iso_ref["evidence"]["text"]


def test_multi_family_fixture_extraction():
    """Verify extraction of IS/IEC, IS/ISO/IEC, ISO/IEC GUIDE, and SP from table fixture."""
    html_path = FIXTURES_DIR / "preview_multi_family_references.html"
    html = html_path.read_text(encoding="utf-8")
    
    parsed = parse_preview_html(html, source_standard="IS 16822:2018")
    formal_refs = parsed["formal_references"]
    
    families_found = {r["target"]["family"] for r in formal_refs}
    assert "IS/IEC" in families_found
    assert "IS/ISO/IEC" in families_found
    assert "ISO/IEC GUIDE" in families_found
    assert "SP" in families_found
    assert "IEC" in families_found
    
    # Check SP 45 has full title and is typed as special publication
    sp_ref = next(r for r in formal_refs if r["target"]["family"] == "SP")
    assert sp_ref["target"]["designation"] == "SP 45:1988"
    assert "Handbook on Glossary of Textile Terms" in sp_ref["title"]


# ── 3. Scope, Foreword, and Prose Relationship Tests ──

def test_scope_extraction_and_missing_scope():
    """Verify Scope presence in preview_is_19901_2026 and clean absence in preview_missing_scope."""
    # 1. Present scope
    html_scope = (FIXTURES_DIR / "preview_is_19901_2026.html").read_text(encoding="utf-8")
    parsed_scope = parse_preview_html(html_scope)
    assert parsed_scope["scope"]["status"] == "present"
    assert parsed_scope["scope"]["extraction_method"] == "html_section"
    assert "biotherapeutic products" in parsed_scope["scope"]["text"]
    
    # 2. Absent scope
    html_missing = (FIXTURES_DIR / "preview_missing_scope.html").read_text(encoding="utf-8")
    parsed_missing = parse_preview_html(html_missing)
    assert parsed_missing["scope"]["status"] == "absent"
    assert parsed_missing["scope"]["text"] is None


def test_national_foreword_prose_reference():
    """Verify extraction of National Foreword and prose reference to IS 302 (Part 1)."""
    html_fw = (FIXTURES_DIR / "preview_is_302_part2_sec16_2026.html").read_text(encoding="utf-8")
    parsed = parse_preview_html(html_fw, source_standard="IS 302 (Part 2/Sec 16):2026")
    
    assert parsed["national_foreword"]["status"] == "present"
    assert "IEC 60335-2-16 : 2022" in parsed["national_foreword"]["text"]
    
    # Check prose references
    prose_refs = parsed["prose_references"]
    assert len(prose_refs) >= 1
    
    p_ref = next(r for r in prose_refs if r["target"]["base_number"] == "302" and r["target"]["part"] == "1")
    assert p_ref["relationship"] == "used_in_conjunction_with"
    assert p_ref["relationship_confidence"] == "explicit_prose"
    assert p_ref["evidence"]["complete"] is True
    assert "used in conjunction with IS 302 (Part 1)" in p_ref["evidence"]["text"]


# ── 4. Page Identity Verification & Fallback Tests ──

def test_page_identity_verification_matching(tmp_path):
    """Verify family-aware identity verification: MATCH, MISMATCH, and UNKNOWN."""
    fetcher = PreviewFetcher(cache_dir=tmp_path)
    
    # MATCH
    html_19901 = (FIXTURES_DIR / "preview_is_19901_2026.html").read_text(encoding="utf-8")
    req_19901 = parse_standard_identity("IS 19901:2026")
    status, reason, evidence = fetcher.verify_page_identity(req_19901, html_19901)
    assert status in ("match", "match_version_verified")
    assert reason is None
    assert evidence["header_text"].startswith("IS 19901 : 2026")
    
    # MATCH with Part and Section
    html_302 = (FIXTURES_DIR / "preview_is_302_part2_sec16_2026.html").read_text(encoding="utf-8")
    req_302 = parse_standard_identity("IS 302 (Part 2/Sec 16):2026")
    status, reason, evidence = fetcher.verify_page_identity(req_302, html_302)
    assert status in ("match", "match_version_verified")
    
    # MISMATCH: Base number
    req_wrong_base = parse_standard_identity("IS 19897:2026")
    status, reason, _ = fetcher.verify_page_identity(req_wrong_base, html_19901)
    assert status == "mismatch"
    assert "Base number mismatch" in reason
    
    # MISMATCH: Part/Section
    req_wrong_sec = parse_standard_identity("IS 302 (Part 2/Sec 21):2026")
    status, reason, _ = fetcher.verify_page_identity(req_wrong_sec, html_302)
    assert status == "mismatch"
    assert "Section mismatch" in reason
    
    # MISMATCH: Family (IS vs IS/IEC)
    html_wrong_fam = (FIXTURES_DIR / "preview_wrong_family.html").read_text(encoding="utf-8")
    req_plain_is = parse_standard_identity("IS 61439:2020")
    status, reason, _ = fetcher.verify_page_identity(req_plain_is, html_wrong_fam)
    assert status == "mismatch"
    assert "Family mismatch" in reason
    
    # UNKNOWN: Page has no recognizable standard number in header
    html_unknown = (FIXTURES_DIR / "preview_unknown_identity.html").read_text(encoding="utf-8")
    status, reason, _ = fetcher.verify_page_identity(req_19901, html_unknown)
    assert status == "unknown"
    
    # Page with IS title and IS/IEC, IS/ISO/IEC references in Section 2 table should match IS 16822, not referenced families
    html_with_refs = (FIXTURES_DIR / "preview_multi_family_references.html").read_text(encoding="utf-8")
    req_multi = parse_standard_identity("IS 16822:2018")
    status, reason, evidence = fetcher.verify_page_identity(req_multi, html_with_refs)
    assert status in ("match", "match_version_verified")
    assert evidence["header_text"].startswith("IS 16822 : 2018")


def test_preview_id_candidates_with_publish_date():
    """Verify that publish_date provides an alternative year candidate when different."""
    cands = standard_number_to_preview_id_candidates("IS 19519:2025", publish_date="29 May 2026")
    assert cands == ["19519_2025", "19519", "19519_2026"]
    
    # If date has same year, no duplicate added
    cands_same = standard_number_to_preview_id_candidates("IS 19901:2026", publish_date="01 Jan 2026")
    assert cands_same == ["19901_2026", "19901"]


def test_fetch_with_fallback_rejection_and_acceptance(tmp_path):
    """Verify fallback behavior: empty primary falls back to matching secondary; wrong secondary is rejected."""
    fetcher = PreviewFetcher(cache_dir=tmp_path)
    
    # Prime cache:
    # 17424_1_2020 is an empty shell (~1150 bytes)
    # 17424_1 is valid preview_is_17424_part1_2020.html
    (tmp_path / "17424_1_2020.html").write_text("<html><body>Empty shell page</body></html>", encoding="utf-8")
    (tmp_path / "17424_1.html").write_text((FIXTURES_DIR / "preview_is_17424_part1_2020.html").read_text(encoding="utf-8"), encoding="utf-8")
    
    req_identity = parse_standard_identity("IS 17424 (Part 1):2020")
    result = fetcher.fetch_with_fallback(["17424_1_2020", "17424_1"], requested_identity=req_identity)
    
    assert result["fetch_status"] == "success"
    assert result["identity_match"] in ("match", "match_version_verified")
    assert result["matched_preview_id"] == "17424_1"
    
    # Now test wrong standard fallback rejection:
    # Candidate 2 is preview_wrong_standard.html
    (tmp_path / "99999_wrong.html").write_text((FIXTURES_DIR / "preview_wrong_standard.html").read_text(encoding="utf-8"), encoding="utf-8")
    result_reject = fetcher.fetch_with_fallback(["17424_1_2020", "99999_wrong"], requested_identity=req_identity)
    assert result_reject["fetch_status"] == "failed"
    assert result_reject["identity_match"] == "unknown"


# ── 5. End-to-End Idempotency & Resumption Tests ──

def test_collector_idempotency_no_duplicates(tmp_path):
    """Verify that running the collector multiple times produces identical, zero-duplicate JSONL files."""
    # 1. Create a minimal Excel test file
    excel_file = tmp_path / "test_input.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Standards"
    ws.append(["Standard Number", "Title", "Date of Publish", "Type of Standard", "Degree of Equivalence"])
    ws.append(["IS 19901:2026", "Safe Handling of Biotherapeutic Products", "2026-01-01", "Standard", None])
    ws.append(["IS 17424 (Part 1):2020", "Ayurvedic Terminology Fundamental Principles", "2020-01-01", "Standard", None])
    wb.save(excel_file)
    
    # 2. Prime cache for offline test
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "19901_2026.html").write_text((FIXTURES_DIR / "preview_is_19901_2026.html").read_text(encoding="utf-8"), encoding="utf-8")
    (raw_dir / "17424_1.html").write_text((FIXTURES_DIR / "preview_is_17424_part1_2020.html").read_text(encoding="utf-8"), encoding="utf-8")
    
    out_dir = tmp_path / "processed"
    
    # Run 1: initial run
    c1 = Collector(
        input_excel=excel_file,
        department="TEST",
        output_dir=out_dir,
        raw_dir=raw_dir,
        reports_dir=tmp_path / "reports",
        logs_dir=tmp_path / "logs",
        parse_cache_only=True,
    )
    rep1 = c1.run()
    
    std_jsonl = out_dir / "TEST_standards.jsonl"
    ref_jsonl = out_dir / "TEST_references.jsonl"
    avail_jsonl = out_dir / "TEST_source_availability.jsonl"
    
    assert std_jsonl.exists()
    assert ref_jsonl.exists()
    assert avail_jsonl.exists()
    
    lines_std_1 = std_jsonl.read_text(encoding="utf-8").strip().splitlines()
    lines_ref_1 = ref_jsonl.read_text(encoding="utf-8").strip().splitlines()
    lines_avail_1 = avail_jsonl.read_text(encoding="utf-8").strip().splitlines()
    
    assert len(lines_std_1) == 2
    assert len(lines_avail_1) == 2
    
    # Run 2: re-run on same input
    c2 = Collector(
        input_excel=excel_file,
        department="TEST",
        output_dir=out_dir,
        raw_dir=raw_dir,
        reports_dir=tmp_path / "reports",
        logs_dir=tmp_path / "logs",
        parse_cache_only=True,
    )
    rep2 = c2.run()
    
    lines_std_2 = std_jsonl.read_text(encoding="utf-8").strip().splitlines()
    lines_ref_2 = ref_jsonl.read_text(encoding="utf-8").strip().splitlines()
    lines_avail_2 = avail_jsonl.read_text(encoding="utf-8").strip().splitlines()
    
    # CRITICAL IDEMPOTENCY ASSERTION: exactly equal counts, zero duplicates accumulated
    assert len(lines_std_2) == len(lines_std_1) == 2
    assert len(lines_ref_2) == len(lines_ref_1)
    assert len(lines_avail_2) == len(lines_avail_1) == 2
    
    # Validate canonical records schema
    rec0 = json.loads(lines_std_2[0])
    assert rec0["record_version"] == "1.2"
    assert rec0["identity"]["standard_designation"] == "IS 19901:2026"
    assert rec0["content"]["scope"]["status"] == "present"
    assert rec0["source"]["identity_match"] in ("match", "match_version_verified")
    assert rec0["source"]["page_identity_evidence"]["verification_method"] == "header_parser"
