# Regulatory Data Verification Report
**Date:** 2026-09-28
**Scope:** Cross-reference `source_manifest.json` vs `qco_orders.jsonl`

## Summary of Discrepancies Found

### 1. Cement QCO — Conflicting Order/Year/Gazette
| Field | source_manifest.json | qco_orders.jsonl |
|-------|---------------------|-------------------|
| Order Title | "Cement (Quality Control) Order, **2024**" | "Cement (Quality Control) Order, **2003** (as amended)" |
| Gazette Ref | S.O. **2282(E)** | S.O. **191(E)** |
| Source URL | `.../2024/254922.pdf` | `.../2003/191_E.pdf` |
| Source Artifact | `egazette_so_2282_e_2024.pdf` | `egazette_so_191_e_2023.pdf` (year mismatch in filename too) |

**Assessment:** The two files describe **different orders**. There IS a 2003 Cement QCO (S.O. 191(E)) and there IS a 2024 Cement amendment (S.O. 2282(E)). However, the JSONL record mixes both — it says "2003 (as amended)" but references the 2024 gazette URL and 2024 standard_coverage. The JSONL's `standard_designations` includes `IS 6452:2026` which is anachronistic for a 2003 order and suspicious for 2024 (IS 6452 is currently at 2001 edition).

### 2. Steel Products QCO — PDF URL Mismatch
| Field | source_manifest.json | qco_orders.jsonl |
|-------|---------------------|-------------------|
| Source URL | `...2024/256976.pdf` | `...2024/256716.pdf` |

**Assessment:** One of the PDF URLs is wrong. The gazette reference (S.O. 3716(E)) is consistent across both.

### 3. Smart Meters QCO — Title and Standards Mismatch
| Field | source_manifest.json | qco_orders.jsonl |
|-------|---------------------|-------------------|
| Order Title | "Electricity Meters (Quality Control) Order, 2023" | "Smart Meters (Quality Control) Order, 2023" |
| Standard Coverage | IS 1239, IS 1786, IS 2062, IS 800 | IS 16444 (Part 1), IS 16444 (Part 2), IS 15884, IS 13779 |
| Includes IS 14697? | Yes | No |

**Assessment:** The manifest entry for "Smart Meters" includes IS standards for **steel products** (IS 1239, IS 1786, etc.) — this appears to be a copy-paste error. The JSONL uses "Smart Meters" as title while the manifest uses "Electricity Meters" — both are arguably correct names, but the standard_coverage list in the manifest is clearly wrong (contains steel standards).

### 4. MeitY CRS LED — Title and Standards Mismatch
| Field | source_manifest.json | qco_orders.jsonl |
|-------|---------------------|-------------------|
| Order Title | "...Order, **Phase II**" | "...Order, **2012** (as amended)" |
| Includes IS 16103 (Part 1)? | No | Yes |

**Assessment:** The manifest describes Phase II of the CRS order, while the JSONL describes the 2012 order (amended). These may be the same order with different naming. However, the JSONL adds `IS 16103 (Part 1)` to `standard_designations` that is not in the manifest's `standard_coverage`, raising a question about its source.

### 5. Anachronistic Standard Editions
- JSONL Record #5 (Cement): lists `IS 6452:2026` and `IS 455:2015` for an order dated 2003. IS 6452:2026 is a future-dated standard that would not have existed when the 2003 order was published.
- JSONL Record #7 (Electrical Appliances, 2023): lists `IS 302 (Part 2/Sec 16):2026` — another future-dated standard edition.

**Assessment:** Future-dated editions (`:2026`) in records about older orders are suspicious. This data may have been generated from a future-version standards knowledge base that did not exist at the time of publication.

### 6. Effective Date Anomaly
- JSONL Record #3 (Steel, 2024): publication_date = 2024-08-29, effective_date = 2024-08-29 (same day). QCO orders typically have a 6-month gap between publication and effective date.

**Assessment:** Immediate effective date is unusual but not impossible — some urgent orders take effect immediately. Requires verification against the actual gazette text.

## Data Integrity Summary

| Check | Result |
|-------|--------|
| Record count | JSONL has 12 records, manifest has 13 sources ✓ |
| Gazette reference consistency | 2 mismatches (Cement, Steel URL) ✗ |
| Order title consistency | 2 mismatches (Cement, Smart Meters) ✗ |
| Standard listing consistency | 3 mismatches (Smart Meters, CRS LED, additional standards in JSONL) ✗ |
| Anachronistic editions | 2 future-dated standards (IS 6452:2026, IS 302 Part 2/Sec 16:2026) ✗ |
| Effective date plausibility | 1 anomaly (Steel, same-day effective) ? |

**Confidence Level: Moderate** — WebFetch verification against live e-Gazette PDFs could not be completed (WebFetch endpoint unavailable). Findings are based on internal cross-referencing between the two data files plus domain knowledge of BIS/Indian Standards practices.
