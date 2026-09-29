"""Diagnostic: run parser on real cached HTML and report reference counts."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')
from src.parser import parse_preview_html

def analyze(name, filepath, expected_rows=None, expected_refs=None):
    print(f"\n{'='*60}")
    print(f"{name}")
    print(f"{'='*60}")
    if not os.path.exists(filepath):
        print("  FILE NOT FOUND")
        return
    html = open(filepath, 'r', encoding='utf-8').read()
    result = parse_preview_html(html, source_standard=name)
    
    formal = result['formal_references']
    prose = result['prose_references']
    
    # Reference count metrics
    refs_count = len(formal)
    dual_count = sum(1 for r in formal if r.get('relationship') == 'dual_numbering')
    continuation_count = sum(1 for r in formal if r.get('evidence', {}).get('continuation_resolved'))
    
    print(f"  extracted_references: {refs_count}")
    print(f"  dual_numbered: {dual_count}")
    print(f"  continuation_resolved: {continuation_count}")
    if expected_refs:
        status = "PASS" if refs_count >= expected_refs else "FAIL"
        print(f"  expected >= {expected_refs}: {status}")
    
    # ICS
    print(f"  ics_raw: {result.get('ics_raw')}")
    print(f"  ics_codes: {result.get('ics_codes')}")
    
    # List all references
    for r in formal:
        d = r['target']['designation']
        rel = r.get('relationship', '')
        linked = r.get('linked_standard', '')
        cont = ' [continuation]' if r.get('evidence', {}).get('continuation_resolved') else ''
        dual_raw = f" raw=[{r.get('dual_numbering_raw', '')}]" if r.get('dual_numbering_raw') else ''
        print(f"    {d} | {rel}{cont}{dual_raw}")
        if linked:
            print(f"      └─ linked_to: {linked}")

# Test standards
analyze("IS 19415:2025", "data/raw/preview_html/19415_2025.html", expected_rows=25)
analyze("IS 19084:2024", "data/raw/preview_html/19084_2024.html", expected_rows=14)
analyze("IS 19355:2025", "data/raw/preview_html/19355_2025.html", expected_rows=14)
analyze("IS 17873:2022", "data/raw/preview_html/17873_2022.html")

# ICS cases
for name, path in [
    ("IS 18750 (Part 8/Sec 3):2026", "data/raw/preview_html/18750_8_3_2026.html"),
    ("IS 18750 (Part 5):2024", "data/raw/preview_html/18750_5_2024.html"),
    ("IS 18750 (Part 1):2024", "data/raw/preview_html/18750_1_2024.html"),
    ("IS 18750 (Part 2):2024", "data/raw/preview_html/18750_2_2024.html"),
    ("IS 18750 (Part 3):2024", "data/raw/preview_html/18750_3_2024.html"),
]:
    html = open(path, 'r', encoding='utf-8').read()
    r = parse_preview_html(html)
    print(f"\n{name}: ics_raw='{r.get('ics_raw')}' ics_codes={r.get('ics_codes')}")
