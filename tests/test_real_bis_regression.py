"""
P6: Real-BIS Regression Tests — V1.2 Audit
============================================
Tests against actual cached BIS Preview HTML from the AYUSH dataset.
Each test uses explicit identity-level assertions (not just total-count).

Two separate metrics per standard:
    formal_reference_rows   = BIS table rows (ground truth from HTML)
    extracted_references    = individual IS/ISO/SP standards after continuation + dual-numbering

Test H: Continuation state reset — ensures (Part X) after a new complete
        IS designation belongs to the NEW standard, not the previous one.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parser import parse_preview_html, _extract_ics_codes, _split_dual_numbered
from bs4 import BeautifulSoup


PREVIEW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "preview_html")


def _load_and_parse(filename, source_standard=None):
    path = os.path.join(PREVIEW_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"Cached HTML not found: {filename}")
    html = open(path, "r", encoding="utf-8").read()
    return parse_preview_html(html, source_standard=source_standard)


# ── Test A: IS 18750 Part 8/Sec 3 — Multi-ICS with semicolon ──

class TestA_ICS_Semicolon:
    def test_ics_raw_preserved(self):
        result = _load_and_parse("18750_8_3_2026.html")
        assert result["ics_raw"] == "ICS 01.040.11; 111.020.99"

    def test_ics_codes_exact(self):
        result = _load_and_parse("18750_8_3_2026.html")
        assert result["ics_codes"] == ["01.040.11", "111.020.99"]


# ── Test B: IS 18750 Part 5 — Multi-ICS, NO normalization ──

class TestB_ICS_NoNormalization:
    def test_ics_raw_preserved(self):
        result = _load_and_parse("18750_5_2024.html")
        assert result["ics_raw"] == "ICS 01.04.11, 11.020.99"

    def test_ics_codes_not_normalized(self):
        """01.04.11 must NOT be silently normalized to 01.040.11"""
        result = _load_and_parse("18750_5_2024.html")
        assert "01.04.11" in result["ics_codes"]
        assert "01.040.11" not in result["ics_codes"]
        assert "11.020.99" in result["ics_codes"]


# ── Test C: IS 19415 — Continuation + dual-numbering (the critical test) ──

class TestC_IS19415_Continuation:
    """
    IS 19415:2025 has 25 BIS reference rows.
    After continuation resolution and dual-number splitting: 33 extracted references.
    """
    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = _load_and_parse("19415_2025.html", source_standard="IS 19415:2025")
        self.refs = self.result["formal_references"]
        self.desigs = [r["target"]["designation"] for r in self.refs]

    def test_total_extracted_references(self):
        assert len(self.refs) == 33

    def test_dual_numbered_count(self):
        dual = [r for r in self.refs if r["relationship"] == "dual_numbering"]
        assert len(dual) == 8

    def test_continuation_resolved_count(self):
        cont = [r for r in self.refs if r.get("evidence", {}).get("continuation_resolved")]
        assert len(cont) == 7

    # Identity-level assertions for continuation rows
    def test_is5887_part3_sec1(self):
        assert "IS 5887 (Part 3/Sec 1):2020" in self.desigs

    def test_iso6579_1_linked(self):
        assert "ISO 6579-1:2017" in self.desigs
        iso = [r for r in self.refs if r["target"]["designation"] == "ISO 6579-1:2017"][0]
        assert iso["relationship"] == "dual_numbering"
        assert iso["linked_standard"] == "IS 5887 (Part 3/Sec 1):2020"

    def test_is5887_part8_exists(self):
        assert "IS 5887 (Part 8)" in self.desigs

    def test_is5887_part8_sec1(self):
        assert "IS 5887 (Part 8/Sec 1):2023" in self.desigs

    def test_is5887_part8_sec2(self):
        assert "IS 5887 (Part 8/Sec 2):2023" in self.desigs

    def test_iso6888_1_linked(self):
        assert "ISO 6888-1:2021" in self.desigs
        iso = [r for r in self.refs if r["target"]["designation"] == "ISO 6888-1:2021"][0]
        assert iso["linked_standard"] == "IS 5887 (Part 8/Sec 1):2023"

    def test_iso6888_2_linked(self):
        assert "ISO 6888-2:2021" in self.desigs
        iso = [r for r in self.refs if r["target"]["designation"] == "ISO 6888-2:2021"][0]
        assert iso["linked_standard"] == "IS 5887 (Part 8/Sec 2):2023"

    def test_iso_ts_11059(self):
        """ISO/TS family must be recognized"""
        assert "ISO/TS 11059:2009" in self.desigs
        ts = [r for r in self.refs if r["target"]["designation"] == "ISO/TS 11059:2009"][0]
        assert ts["relationship"] == "dual_numbering"
        assert ts["linked_standard"] == "IS 18107:2023"

    # Non-continuation rows should also be present
    def test_simple_refs_preserved(self):
        assert "IS 460 (Part 1):2020" in self.desigs
        assert "IS 1000:2021" in self.desigs
        assert "ISO 22662:2024" in self.desigs

    def test_dual_number_no_space(self):
        """IS 16424 : 2016/ISO 7251 : 2005 (no space around /)"""
        assert "IS 16424:2016" in self.desigs
        assert "ISO 7251:2005" in self.desigs


# ── Test D: IS 19084 — Dual-numbered (no continuation) ──

class TestD_IS19084_DualNumbered:
    """
    IS 19084:2024 has 14 BIS reference rows.
    After dual-number splitting: 16 extracted references.
    """
    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = _load_and_parse("19084_2024.html", source_standard="IS 19084:2024")
        self.refs = self.result["formal_references"]
        self.desigs = [r["target"]["designation"] for r in self.refs]

    def test_total_extracted_references(self):
        assert len(self.refs) == 16

    def test_dual_numbered_count(self):
        dual = [r for r in self.refs if r["relationship"] == "dual_numbering"]
        assert len(dual) == 2

    def test_is2828_iso472(self):
        assert "IS 2828:2019" in self.desigs
        assert "ISO 472:2013" in self.desigs
        iso = [r for r in self.refs if r["target"]["designation"] == "ISO 472:2013"][0]
        assert iso["relationship"] == "dual_numbering"
        assert iso["linked_standard"] == "IS 2828:2019"

    def test_is4905_iso24153(self):
        assert "IS 4905:2015" in self.desigs
        assert "ISO 24153:2009" in self.desigs
        iso = [r for r in self.refs if r["target"]["designation"] == "ISO 24153:2009"][0]
        assert iso["relationship"] == "dual_numbering"
        assert iso["linked_standard"] == "IS 4905:2015"


# ── Test E: IS 19355 — Dual-numbered with 3 pairs ──

class TestE_IS19355_DualNumbered:
    """
    IS 19355:2025 has 14 BIS reference rows.
    After dual-number splitting: 17 extracted references.
    """
    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = _load_and_parse("19355_2025.html", source_standard="IS 19355:2025")
        self.refs = self.result["formal_references"]
        self.desigs = [r["target"]["designation"] for r in self.refs]

    def test_total_extracted_references(self):
        assert len(self.refs) == 17

    def test_dual_numbered_count(self):
        dual = [r for r in self.refs if r["relationship"] == "dual_numbering"]
        assert len(dual) == 3

    def test_is11539_iso8113(self):
        assert "IS 11539:2018" in self.desigs
        assert "ISO 8113:2004" in self.desigs

    def test_is18219_iso3585(self):
        assert "IS 18219:2023" in self.desigs
        assert "ISO 3585:1998" in self.desigs

    def test_is18319_iso17665(self):
        assert "IS 18319:2024" in self.desigs
        assert "ISO 17665:2024" in self.desigs


# ── Test F: IS 17873 — Baseline preserved (16 refs) ──

class TestF_IS17873_Baseline:
    def test_total_references(self):
        result = _load_and_parse("17873_2022.html", source_standard="IS 17873:2022")
        refs = result["formal_references"]
        # Previously 16 when bare numeric standards were missed; now 20 with bare numeric standards recovered
        assert len(refs) == 20
        desigs = {r["target"]["designation"] for r in refs}
        assert "IS 1390:2019" in desigs
        assert "ISO 3071:2005" in desigs
        assert "IS 1954:1990" in desigs
        assert "IS 1963:2004" in desigs
        assert "IS 1964:2001" in desigs

    def test_ics_raw(self):
        result = _load_and_parse("17873_2022.html")
        assert result["ics_raw"] == "ICS 59.080.60, 97.220.01"
        assert result["ics_codes"] == ["59.080.60", "97.220.01"]


# ── Test G: No "Referred in" in preview HTML ──

class TestG_NoReverseRefsInPreview:
    """BSB Edge preview pages do NOT contain 'Referred in' sections.
    If any standard had reverse refs, they should NOT appear."""
    def test_19084_no_reverse(self):
        result = _load_and_parse("19084_2024.html", source_standard="IS 19084:2024")
        for ref in result["formal_references"]:
            assert ref.get("relationship") != "reverse_reference"


# ── Test H: Continuation state reset ──

class TestH_ContinuationReset:
    """
    When a new complete IS designation appears, the continuation state
    must reset. (Part X) after the new standard belongs to IT, not the
    previous base.

    This prevents silent corruption where valid-looking standard numbers
    are attached to the wrong base.
    """
    def test_continuation_resets_on_new_standard(self):
        """Simulates:
        IS 5887      (base A)
        (Part 8)     (continuation of A)
        IS 16069 (Part 2) : 2013/ISO 21527-2 : 2008  (new complete standard B)
        IS 16424 : 2016/ISO 7251 : 2005              (new complete standard C)
        """
        html = """
        <html><body>
        <p>SCOPE</p><p>Test scope.</p>
        <b>REFERENCES</b>
        <table>
          <tr><td>IS No.</td><td>Title</td></tr>
          <tr><td>IS 5887</td><td>Methods for detection</td></tr>
          <tr><td>(Part 8)</td><td>Staphylococci enumeration</td></tr>
          <tr><td>IS 16069 (Part 2) : 2013/ISO 21527-2 : 2008</td><td>Yeasts and moulds</td></tr>
          <tr><td>IS 16424 : 2016/ISO 7251 : 2005</td><td>E. coli detection</td></tr>
        </table>
        </body></html>
        """
        result = parse_preview_html(html, source_standard="IS 99999:2025")
        refs = result["formal_references"]
        desigs = [r["target"]["designation"] for r in refs]

        # IS 5887 and IS 5887 (Part 8) should exist
        assert "IS 5887" in desigs
        assert "IS 5887 (Part 8)" in desigs

        # IS 16069 should be its own standard (NOT IS 5887 (Part X))
        assert "IS 16069 (Part 2):2013" in desigs
        assert "ISO 21527-2:2008" in desigs

        # IS 16424 should be its own standard
        assert "IS 16424:2016" in desigs
        assert "ISO 7251:2005" in desigs

        # Verify no reference is wrongly attached to IS 5887
        assert "IS 5887 (Part 16069)" not in desigs  # would be corrupted

    def test_continuation_resets_in_real_data(self):
        """IS 19415 has IS 5887 → continuation → IS 7017 (new standard).
        IS 7017 must NOT be a continuation of IS 5887."""
        result = _load_and_parse("19415_2025.html", source_standard="IS 19415:2025")
        desigs = [r["target"]["designation"] for r in result["formal_references"]]
        assert "IS 7017:1973" in desigs
        # IS 7017 should not have any Part attached
        is7017 = [d for d in desigs if d.startswith("IS 7017")]
        assert is7017 == ["IS 7017:1973"]


# ── Test I: Structured dual-numbering output ──

class TestI_StructuredDualNumbering:
    def test_split_returns_structured_data(self):
        result = _split_dual_numbered("IS 2828 : 2019/ISO 472 : 2013")
        assert len(result) == 2
        assert result[0]["text"] == "IS 2828 : 2019"
        assert result[0]["is_dual"] is True
        assert result[0]["raw"] == "IS 2828 : 2019/ISO 472 : 2013"
        assert result[1]["text"] == "ISO 472 : 2013"
        assert result[1]["is_dual"] is True

    def test_single_standard_returns_not_dual(self):
        result = _split_dual_numbered("IS 460 (Part 1) : 2020")
        assert len(result) == 1
        assert result[0]["is_dual"] is False

    def test_no_split_on_arbitrary_slash(self):
        """Don't split arbitrary text with / that isn't dual-numbering"""
        result = _split_dual_numbered("Testing / something else")
        assert len(result) == 1
        assert result[0]["is_dual"] is False

    def test_dual_numbering_not_equivalent_to(self):
        """dual_numbering is NOT converted to equivalent_to"""
        result = _load_and_parse("19084_2024.html", source_standard="IS 19084:2024")
        refs = result["formal_references"]
        for r in refs:
            assert r["relationship"] != "equivalent_to"


# ── Test J: Status semantics ──

class TestJ_StatusSemantics:
    def test_present_when_found(self):
        result = _load_and_parse("19415_2025.html")
        assert result["scope"]["status"] == "present"

    def test_absent_when_genuinely_missing(self):
        """National foreword is genuinely absent from most AYUSH previews"""
        result = _load_and_parse("19415_2025.html")
        assert result["national_foreword"]["status"] == "absent"


# ── Test K: Bare Numeric References and Annex Status Classification ──

class TestK_BareNumericReferencesAndAnnexStatus:
    def test_bare_numeric_extraction_17924(self):
        result = _load_and_parse("17924_2022.html", source_standard="IS 17924:2022")
        refs = result["formal_references"]
        desigs = {r["target"]["designation"] for r in refs}
        assert "IS 1070:1992" in desigs
        assert "IS 11380:1985" in desigs
        assert result["references_status"] == "parsed"
        # Check evidence captures bare number resolution
        ref_1070 = next(r for r in refs if r["target"]["designation"] == "IS 1070:1992")
        assert ref_1070["evidence"]["bare_number_resolved"] is True
        assert "1070 : 1992" in ref_1070["evidence"]["text"]

    def test_bare_numeric_with_dual_numbering_18098(self):
        result = _load_and_parse("18098_2022.html", source_standard="IS 18098:2022")
        refs = result["formal_references"]
        desigs = {r["target"]["designation"] for r in refs}
        assert "IS 1070:1992" in desigs
        assert "IS 17924:2022" in desigs
        assert "IS 13859:1993" in desigs
        assert "ISO 7513:1990" in desigs
        assert "IS 16287:2015" in desigs
        assert "ISO 16050:2003" in desigs
        assert result["references_status"] == "parsed"

    def test_annex_a_reference_status_18172(self):
        result = _load_and_parse("18172_2023.html", source_standard="IS 18172:2023")
        assert len(result["formal_references"]) == 0
        assert result["references_status"] == "referenced_in_annex_not_in_preview"
