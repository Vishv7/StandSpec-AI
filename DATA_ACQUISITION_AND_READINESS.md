# DATA_ACQUISITION_AND_READINESS.md — Data Acquisition Protocols & Readiness Matrix
## StandSpec AI — Source Data Coverage, Department Scaling, and Full PDF Protocols

---

## 1. Executive Summary & Readiness Declaration

StandSpec AI operates on an evidence-first principle: every standard recommendation, clause citation, and regulatory requirement must be backed by verifiable source documents. This document details the data readiness of existing pilot data, the boundaries of preview HTML, and the protocol for scaling into Electrotechnical (ETD) and other core engineering departments.

---

## 2. Field-by-Field Data Readiness Matrix

The following matrix audits every core field extracted by Layer 1 (Collector) and its readiness for the downstream knowledge and recommendation engines:

| Field Name | Extraction Target | Completeness (Pilot) | Quality & Precision | Downstream Engine Impact | Status |
|---|---|---|---|---|---|
| **Standard Designation** | `standard_designation` (e.g. `IS 17873:2022`) | 247 / 247 (100.0%) | Canonical BIS format | Primary identifier and retrieval target | **READY** |
| **Base, Part, Sec, Year** | Structured identity fields | 247 / 247 (100.0%) | Deterministic regex extraction | Hierarchical part matching and temporal queries | **READY** |
| **Title (English)** | Stripped of designation prefix | 247 / 247 (100.0%) | Cleaned, unpolluted title string | Semantic embedding and BM25 index | **READY** |
| **Scope Text** | `scope.text` | 246 / 247 (99.6%) | Direct from HTML Clause 1 | Semantic chunking & candidate reranking | **READY** |
| **Scope Status Flag** | `scope.status` (`present` / `fallback` / `absent`) | 247 / 247 (100.0%) | Transparent provenance | Weights fallback scopes lower during retrieval | **READY** |
| **ICS Codes** | `ics_codes` (list) + `ics_raw` (string) | 246 / 247 (99.6%) | Preserved exactly without mutation | International taxonomy filtering | **READY** |
| **Technical Committee** | `technical_committee` (e.g. `FAD 26`) | 246 / 247 (99.6%) | False-positive hardened | Departmental clustering & routing | **READY** |
| **Normative References** | `formal_references` list | 1153 edges extracted | High-precision table & paragraph extraction | Graph-RAG expansion for allied standards | **READY** |
| **Dual Numbering** | `relationship: dual_numbering` | 156 edges extracted | International adoption preserved | Resolves ISO/IEC counterpart queries | **READY** |
| **References Status** | `references_status` | 247 / 247 (100.0%) | Distinguishes Annex A deferral from absence | Informs engine when full PDF is required | **READY** |

---

## 3. Structural Boundaries of Preview HTML

Understanding the physical boundaries of BSB Edge preview pages is vital for system expectations:

1. **Included in Preview HTML:**
   - Document Title and Designation Header.
   - ICS Classification and Technical Committee Code.
   - National Foreword (when present).
   - Clause 1: Scope (full or preliminary paragraphs).
   - Clause 2: Normative References (when directly printed in text).
2. **Excluded from Preview HTML (Requires Full PDF):**
   - **Normative Annexes (Annex A):** 130 standards in the pilot dataset state *"The standards listed in Annex A contain provisions..."*. Annex A is positioned at the back of the standard document, outside the preliminary preview HTML.
   - **Technical Clause Bodies (Clauses 3 to 15):** Detailed parameter tables, permissible dimensional tolerances, and chemical thresholds.
   - **Drawings and Figures:** Engineering schematics and test rig diagrams.

---

## 4. Full PDF Acquisition Protocol for Critical Standards

For core tender standards where deep clause verification is required:

1. **Priority Selection Criteria:**
   - Standards that are statutory QCO targets (e.g. cables, steel, cement).
   - Top-degree hub standards identified in `standards_graph.json` (e.g. `IS 1070`, `IS 694`, `IS 7098`).
2. **Storage Architecture:**
   - Raw PDFs are stored in `data/raw/full_pdf/<standard_designation>.pdf`.
   - Ingestion scripts extract full Annex A reference lists and clause-level parameter tables.
3. **Traceability:**
   - Extracted clauses record `page_number`, `clause_number`, and `sha256` hash of the parent PDF.

---

## 5. Electrotechnical Department (ETD) Scaling Plan

When scaling into Phase 1 ETD ingestion:
1. Load official `data/raw/ETD_Standards_Catalogue.xlsx`.
2. Inspect column headers and verify standard number formats (`IS 7098 (Part 1)`, `IS 302 (Part 2/Sec 3)`).
3. Execute polite fetching or offline parse with `--department ETD`.
4. Validate ETD outputs against schema and rebuild `standards_graph.json`.
