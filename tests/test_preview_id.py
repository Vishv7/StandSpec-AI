"""
Tests for the preview-ID generator.
Must pass ALL 4 confirmed mappings from COLLECTOR_CONTEXT.md §3.1
before any network requests are made.
"""

from src.preview_id import standard_number_to_preview_id
from src.excel_reader import normalize_standard_number


def test_confirmed_mappings():
    """
    Test all 4 confirmed mappings from COLLECTOR_CONTEXT.md §3.1.
    These are the exit criterion for Phase 2 — all must pass exactly.
    """
    test_cases = [
        ("IS 19901:2026", "19901_2026"),
        ("IS 19897:2026", "19897_2026"),
        ("IS 17874 (Part 2):2026", "17874_2_2026"),
        ("IS 302 (Part 2/Sec 16):2026", "302_2_16_2026"),
    ]
    for input_std, expected_id in test_cases:
        result = standard_number_to_preview_id(input_std)
        assert result == expected_id, f"'{input_std}' produced '{result}', expected '{expected_id}'"


def test_edge_cases():
    """Test edge cases and formats the generator should handle or reject."""
    test_cases = [
        ("IS  19901 : 2026", "19901_2026"),            # extra spaces
        ("IS 17874 ( Part 2 ) : 2026", "17874_2_2026"), # spaces in parens
        ("SP 19901:2026", "19901_2026"),
        ("IS/IEC 19901:2026", "iec19901_2026"),          # IS/IEC prefix
        ("IS/IEC/IEEE 60079 (Part 30/Sec 2):2015", "iee60079_30_2_2015"),  # IS/IEC/IEEE prefix
        ("IS 19901", "19901"),                          # no year
        ("", None),
        ("random text", None),
        ("19901:2026", None),                           # missing prefix
    ]
    for input_std, expected_id in test_cases:
        result = standard_number_to_preview_id(input_std)
        assert result == expected_id, f"'{input_std}' produced '{result}', expected '{expected_id}'"


def test_normalizer():
    """Test the standard number normalizer from excel_reader."""
    test_cases = [
        ("IS 302 (Part 2/Sec 16):2026", "IS 302 (Part 2/Sec 16)", 2026, True),
        ("IS 19901:2026", "IS 19901", 2026, True),
        ("IS 17874 (Part 2):2026", "IS 17874 (Part 2)", 2026, True),
        ("", None, None, False),
    ]
    for raw, expected_is, expected_year, expected_recognized in test_cases:
        result = normalize_standard_number(raw)
        assert result["is_number"] == expected_is
        assert result["year"] == expected_year
        assert result["recognized"] == expected_recognized
