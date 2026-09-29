"""
Regulatory Source Validator — StandSpec AI (Layer 3 / Phase P1-D)
Validates QCO orders and CRS rules against:
  1. schemas/regulatory_source.schema.json (Draft 2020-12)
  2. data/regulatory/source_manifest.json (Authoritative Registry)

Enforces:
  - Exact date formats and logical chronology (publication_date <= effective_date)
  - Required, non-empty standard designations
  - Unique source_id per file referencing source_manifest.json
  - Cross-validation of gazette reference, title, source URL, and standard coverage
  - Fail-closed record classification: CONSISTENT, CONFLICTING, or UNVERIFIED

Usage:
    python scripts/validate_regulatory_sources.py
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
SCHEMA_PATH = SCHEMAS_DIR / "regulatory_source.schema.json"
MANIFEST_PATH = PROJECT_ROOT / "data" / "regulatory" / "source_manifest.json"


def normalize_token(s: str) -> str:
    """Normalize whitespace and lowercase for tolerant comparison."""
    if not s:
        return ""
    return " ".join(s.strip().lower().split())


def normalize_desig(desig: str) -> str:
    """Normalize standard designation by removing year and standardizing spacing."""
    if not desig:
        return ""
    base = desig.split(":")[0].strip().lower()
    return " ".join(base.split())


def validate_regulatory_file(
    filepath: Path,
    validator: Draft202012Validator,
    manifest_sources: Dict[str, Dict[str, Any]],
) -> Tuple[List[str], Dict[str, int]]:
    """
    Validates a regulatory JSONL file against schema and manifest registry.
    Returns (errors_list, classification_counts).
    """
    errors: List[str] = []
    counts = {"CONSISTENT": 0, "CONFLICTING": 0, "UNVERIFIED": 0}

    if not filepath.exists():
        errors.append(f"File does not exist: {filepath}")
        return errors, counts

    seen_source_ids = set()

    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {line_num}: JSON decode error: {e}")
                counts["UNVERIFIED"] += 1
                continue

            record_status = "CONSISTENT"
            record_issues = []

            # 1. JSON Schema validation
            schema_errs = list(validator.iter_errors(record))
            if schema_errs:
                for err in schema_errs:
                    record_issues.append(f"Schema error at '{'/'.join(str(p) for p in err.path)}': {err.message}")
                record_status = "UNVERIFIED"

            # 2. Source ID presence & manifest lookup
            source_id = record.get("source_id")
            if not source_id:
                record_issues.append("Missing mandatory 'source_id' property")
                record_status = "UNVERIFIED"
            elif source_id not in manifest_sources:
                record_issues.append(f"Unknown source_id '{source_id}' not found in source_manifest.json")
                record_status = "UNVERIFIED"
            else:
                # Duplicate source_id check
                if source_id in seen_source_ids:
                    record_issues.append(f"Duplicate source_id '{source_id}' found in same file")
                    record_status = "CONFLICTING"
                seen_source_ids.add(source_id)

                # 3. Cross-validate against manifest entry
                manifest_entry = manifest_sources[source_id]

                # Gazette reference
                rec_gazette = normalize_token(record.get("gazette_reference", ""))
                man_gazette = normalize_token(manifest_entry.get("gazette_id", ""))
                if rec_gazette != man_gazette:
                    record_issues.append(
                        f"Gazette reference mismatch: record '{record.get('gazette_reference')}' vs manifest '{manifest_entry.get('gazette_id')}'"
                    )
                    record_status = "CONFLICTING"

                # Order Title
                rec_title = normalize_token(record.get("order_title", ""))
                man_title = normalize_token(manifest_entry.get("order_title", ""))
                if rec_title != man_title:
                    record_issues.append(
                        f"Order title mismatch: record '{record.get('order_title')}' vs manifest '{manifest_entry.get('order_title')}'"
                    )
                    record_status = "CONFLICTING"

                # Source URL
                rec_url = str(record.get("source_url", "")).strip().rstrip("/")
                man_url = str(manifest_entry.get("source_url", "")).strip().rstrip("/")
                if rec_url != man_url:
                    record_issues.append(
                        f"Source URL mismatch: record '{rec_url}' vs manifest '{man_url}'"
                    )
                    record_status = "CONFLICTING"

                # Standard Coverage
                man_coverage_bases = {
                    normalize_desig(c) for c in manifest_entry.get("standard_coverage", [])
                }
                rec_standards = record.get("standard_designations", [])
                uncovered = []
                for s in rec_standards:
                    base_s = normalize_desig(s)
                    if base_s not in man_coverage_bases and not any(
                        base_s.startswith(c) or c.startswith(base_s) for c in man_coverage_bases if c
                    ):
                        uncovered.append(s)

                if uncovered:
                    record_issues.append(
                        f"Standard coverage mismatch: standards {uncovered} present in record but absent from manifest coverage {manifest_entry.get('standard_coverage')}"
                    )
                    record_status = "CONFLICTING"

            # 4. Logical dates validation
            pub_date = record.get("publication_date", "")
            eff_date = record.get("effective_date", "")
            if pub_date and eff_date and eff_date < pub_date:
                record_issues.append(f"Effective date ({eff_date}) precedes publication date ({pub_date})")
                record_status = "CONFLICTING"

            # 5. Non-empty standards
            desigs = record.get("standard_designations", [])
            if not desigs:
                record_issues.append("standard_designations list is empty")
                record_status = "UNVERIFIED"

            # Record result
            order_label = f"{record.get('order_number', 'unknown')} ({source_id or 'NO_SOURCE_ID'})"
            counts[record_status] += 1

            if record_status != "CONSISTENT":
                errors.append(f"Line {line_num} [{order_label}] - {record_status}: " + "; ".join(record_issues))
            else:
                print(f"  [CONSISTENT] Line {line_num}: {order_label}")

    return errors, counts


def main():
    parser = argparse.ArgumentParser(description="Validate Regulatory Source Datasets")
    parser.add_argument("--qco", default="data/regulatory/qco_orders.jsonl", help="Path to QCO orders JSONL")
    parser.add_argument("--crs", default="data/regulatory/crs_rules.jsonl", help="Path to CRS rules JSONL")
    parser.add_argument("--manifest", default="data/regulatory/source_manifest.json", help="Path to source manifest JSON")
    args = parser.parse_args()

    if not SCHEMA_PATH.exists():
        print(f"Error: Schema file missing at {SCHEMA_PATH}")
        sys.exit(1)

    manifest_p = PROJECT_ROOT / args.manifest
    if not manifest_p.exists():
        print(f"Error: Source manifest file missing at {manifest_p}")
        sys.exit(1)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    validator = Draft202012Validator(schema)

    with open(manifest_p, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    manifest_sources = {s["source_id"]: s for s in manifest_data.get("sources", [])}

    qco_p = PROJECT_ROOT / args.qco
    crs_p = PROJECT_ROOT / args.crs

    all_errors = []
    total_counts = {"CONSISTENT": 0, "CONFLICTING": 0, "UNVERIFIED": 0}

    print("=" * 70)
    print("StandSpec AI — Regulatory Source & Manifest Integrity Validation")
    print(f"Manifest Version: {manifest_data.get('manifest_version')} ({len(manifest_sources)} sources)")
    print("=" * 70)

    print(f"\n[1/2] Validating QCO Orders: {qco_p}")
    qco_errors, qco_counts = validate_regulatory_file(qco_p, validator, manifest_sources)
    for k in total_counts:
        total_counts[k] += qco_counts[k]

    if qco_errors:
        print(f"  [FAIL] Found issues in QCO orders:")
        for e in qco_errors:
            print(f"    - {e}")
        all_errors.extend(qco_errors)
    else:
        print(f"  [PASS] All {qco_counts['CONSISTENT']} QCO orders consistent with manifest.")

    print(f"\n[2/2] Validating CRS Rules: {crs_p}")
    crs_errors, crs_counts = validate_regulatory_file(crs_p, validator, manifest_sources)
    for k in total_counts:
        total_counts[k] += crs_counts[k]

    if crs_errors:
        print(f"  [FAIL] Found issues in CRS rules:")
        for e in crs_errors:
            print(f"    - {e}")
        all_errors.extend(crs_errors)
    else:
        print(f"  [PASS] All {crs_counts['CONSISTENT']} CRS rules consistent with manifest.")

    print("\n" + "=" * 70)
    print(f"CLASSIFICATION SUMMARY:")
    print(f"  CONSISTENT : {total_counts['CONSISTENT']}")
    print(f"  CONFLICTING: {total_counts['CONFLICTING']}")
    print(f"  UNVERIFIED : {total_counts['UNVERIFIED']}")
    print("=" * 70)

    if all_errors or total_counts["CONFLICTING"] > 0 or total_counts["UNVERIFIED"] > 0:
        print(f"VALIDATION FAILED: {len(all_errors)} error(s) detected. Fail-closed enforced.")
        sys.exit(1)
    else:
        print("ALL REGULATORY SOURCES & MANIFEST IDENTITIES ARE 100% CONSISTENT.")
        sys.exit(0)


if __name__ == "__main__":
    main()
