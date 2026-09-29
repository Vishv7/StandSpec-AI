"""
Tests for output schema compliance (Frozen V1.1 Data Contract).
Validates that generated JSONL records, reference records, and enriched Excel
match the exact structure expected by StandSpec AI.
"""

import json
from pathlib import Path
from openpyxl import Workbook, load_workbook

from src.collector import Collector

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_v1_1_output_schema_and_excel(tmp_path):
    """Generate outputs using Collector in a temporary directory and verify schemas."""
    # Create test input Excel
    excel_file = tmp_path / "sample_etd.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "ETD Standards"
    ws.append(["Standard Number", "Title", "Date of Publish", "Type of Standard", "Degree of Equivalence"])
    ws.append(["IS 19901:2026", "Safe Handling of Biotherapeutic Products", "2026-01-01", "Safety", None])
    ws.append(["IS 302 (Part 2/Sec 16):2026", "Food Waste Disposers", "2026-01-01", "Safety", None])
    wb.save(excel_file)
    
    # Prime raw cache
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "19901_2026.html").write_text((FIXTURES_DIR / "preview_is_19901_2026.html").read_text(encoding="utf-8"), encoding="utf-8")
    (raw_dir / "302_2_16_2026.html").write_text((FIXTURES_DIR / "preview_is_302_part2_sec16_2026.html").read_text(encoding="utf-8"), encoding="utf-8")
    
    out_dir = tmp_path / "processed"
    
    collector = Collector(
        input_excel=excel_file,
        department="ETD",
        output_dir=out_dir,
        raw_dir=raw_dir,
        reports_dir=tmp_path / "reports",
        logs_dir=tmp_path / "logs",
        parse_cache_only=True,
    )
    report = collector.run()
    
    # 1. Verify standards.jsonl
    std_file = out_dir / "ETD_standards.jsonl"
    assert std_file.exists()
    records = [json.loads(line) for line in std_file.read_text(encoding="utf-8").strip().splitlines()]
    assert len(records) == 2
    
    for rec in records:
        assert rec["record_version"] == "1.2"
        assert "input" in rec
        assert "source_file" in rec["input"]
        assert "raw_standard_number" in rec["input"]
        assert "identity" in rec
        assert "standard_designation" in rec["identity"]
        assert "family" in rec["identity"]
        assert "base_number" in rec["identity"]
        assert "content" in rec
        assert "scope" in rec["content"]
        assert "status" in rec["content"]["scope"]
        assert "national_foreword" in rec["content"]
        assert "notes" in rec["content"]
        assert "source" in rec
        assert "fetch_status" in rec["source"]
        assert "identity_match" in rec["source"]
        assert "quality" in rec
        assert "manual_review_required" in rec["quality"]
        
    # 2. Verify references.jsonl
    ref_file = out_dir / "ETD_references.jsonl"
    assert ref_file.exists()
    refs = [json.loads(line) for line in ref_file.read_text(encoding="utf-8").strip().splitlines()]
    assert len(refs) > 0
    
    for ref in refs:
        assert "source_standard" in ref
        assert "target" in ref
        assert "designation" in ref["target"]
        assert "family" in ref["target"]
        assert "reference_type" in ref
        assert "relationship" in ref
        assert "evidence" in ref
        assert "extraction_method" in ref["evidence"]
        assert "complete" in ref["evidence"]
        
    # 3. Verify source_availability.jsonl
    avail_file = out_dir / "ETD_source_availability.jsonl"
    assert avail_file.exists()
    avails = [json.loads(line) for line in avail_file.read_text(encoding="utf-8").strip().splitlines()]
    assert len(avails) == 2
    for a in avails:
        assert "standard_designation" in a
        assert "preview" in a
        assert "identity" in a["preview"]
        assert "reference_counts" in a
        
    # 4. Verify enriched Excel
    excel_out = out_dir / "ETD_enriched.xlsx"
    assert excel_out.exists()
    wb_out = load_workbook(excel_out)
    ws_out = wb_out.active
    assert ws_out.max_row == 3  # 1 header + 2 data rows
    wb_out.close()

    # 5. Verify references_status is present in content (P0-7 fix)
    for rec in records:
        assert "references_status" in rec["content"], "references_status missing from content"
        assert rec["content"]["references_status"] in (
            "parsed", "referenced_in_annex_not_in_preview",
            "truncated_or_empty_in_preview", "none_found", "absent"
        ), f"Invalid references_status value: {rec['content']['references_status']}"
