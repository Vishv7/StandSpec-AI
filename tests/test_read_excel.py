"""
Tests for Excel reader component (Phase 1).
Validates header detection, column mapping, and row parsing.
"""

from pathlib import Path
from openpyxl import Workbook
from src.excel_reader import process_excel, normalize_standard_number


def test_excel_reader_processing(tmp_path):
    """Verify that process_excel parses standards accurately from Excel."""
    excel_path = tmp_path / "test_standards.xlsx"
    reports_dir = tmp_path / "reports"
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Published Standards"
    
    # Header row
    ws.append([
        "Sl. No.", "Standard Number", "Title", "Date of Publish",
        "Type of Standard", "Degree of Equivalence", "Committee"
    ])
    # Data rows
    ws.append([1, "IS 19901:2026", "Safe Handling of Biotherapeutic Products", "2026-01-15", "Product", "None", "AYD 07"])
    ws.append([2, "IS 302 (Part 2/Sec 16):2026", "Food Waste Disposers", "2026-02-20", "Safety", "Identical", "ETD 32"])
    ws.append([3, "IS 17874 (Part 2):2026", "Ayurvedic Medical Devices", "2026-03-10", "Methods", "None", "AYD 01"])
    wb.save(excel_path)
    
    standards, headers, raw_rows = process_excel(excel_path, reports_dir=reports_dir)
    
    assert len(headers) == 7
    assert len(raw_rows) == 3
    assert len(standards) == 3
    
    s0 = standards[0]
    assert s0["original_standard_number"] == "IS 19901:2026"
    assert s0["is_number"] == "IS 19901"
    assert s0["year"] == 2026
    assert s0["recognized"] is True
    assert s0["title"] == "Safe Handling of Biotherapeutic Products"
    
    s1 = standards[1]
    assert s1["original_standard_number"] == "IS 302 (Part 2/Sec 16):2026"
    assert s1["is_number"] == "IS 302 (Part 2/Sec 16)"
    assert s1["year"] == 2026
    assert s1["recognized"] is True

    # Gate P0-4: Raw Excel row preservation
    assert "raw_excel" in s0
    raw0 = s0["raw_excel"]
    assert raw0["sheet_name"] == "Published Standards"
    assert raw0["row_number"] == 2  # Row 1 is header, Row 2 is first data row
    assert isinstance(raw0["row_sha256"], str)
    assert len(raw0["row_sha256"]) == 64
    assert raw0["columns"]["Standard Number"] == "IS 19901:2026"
    assert raw0["columns"]["Committee"] == "AYD 07"
    assert raw0["columns"]["Sl. No."] == "1"
