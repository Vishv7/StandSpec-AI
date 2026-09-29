# COLLECTOR_GUIDE.md — StandSpec AI Standards Data Collector Manual
## Operational Manual, Data Acquisition Protocols, and Pipeline Engineering Standards

---

## 1. Executive Summary & Purpose

The **StandSpec AI Data Collector** (`src/collector.py`) forms **Layer 1** of the StandSpec AI architecture. Its sole responsibility is the deterministic, polite, and verifiable acquisition and extraction of Indian Standards metadata, scope, forewords, notes, and normative references from official Bureau of Indian Standards (BIS) Excel catalogs and BSB Edge preview pages.

---

## 2. Core Non-Negotiable Operational Rules

### 2.1 Scope & Execution Discipline
1. **Single Department Per Execution:** Never run the collector against more than one department's manifest in a single unattended run. Ingestion is intentional, department-scoped, and manifest-verified.
2. **Offline-First Determinism:** When cached HTML previews exist in `data/raw/preview_html/`, run with `--cache-only` to guarantee zero network latency, zero network leakage, and 100% reproducible parses.
3. **No Phantom Expansion:** Do not combine scraping with RAG indexing, database seeding, or model inference on the fly. The collector is strictly a data preparation and provenance engine.

### 2.2 Rate Limiting & Ethical Acquisition
1. **Polite Request Delays:** Maintain a minimum 1.0 second delay between requests to `standardsbis.bsbedge.com`. Never remove delays or launch multi-threaded hammering against external servers.
2. **Exponential Backoff:** On HTTP `429`, `500`, `502`, `503`, or `504` status codes, back off exponentially with up to 3 retries before marking the row `failed`.
3. **Strict Sequential Access:** Requests are always processed sequentially, preserving host connection health and audit traceability.

### 2.3 Data Integrity & Zero-Fabrication Guarantee
1. **No Value Fabrication:** If Scope, Foreword, Notes, or Normative References are absent from a preview page, they are recorded as `null` with explicit status (`absent` or `fallback`). Never guess, extrapolate, or hallucinate missing data.
2. **Raw Snapshotting Before Parsing:** Every raw HTTP response is saved verbatim to `data/raw/preview_html/<preview_id>.html` before extraction occurs. Parser bug fixes are tested and re-run against local cache without re-fetching from BIS.
3. **Tri-State Status Taxonomies:** Standards exit in exactly one mutually exclusive status: `success`, `partial_success`, or `failed`. Quality flags (`manual_review_required`) are orthogonal attributes.

---

## 3. CLI Reference & Operational Commands

### 3.1 Basic Usage

```bash
# 1. Run offline parse on existing cached preview files (Recommended for local evaluation)
python src/collector.py --input data/raw/ayush_standards.xlsx --department FAD --cache-only

# 2. Force re-parse of cached files when parser or schema version changes
python src/collector.py --input data/raw/ayush_standards.xlsx --department FAD --cache-only --force-reparse

# 3. Live collection for a new department (polite fetching with 1.0s throttle)
python src/collector.py --input data/raw/ETD_Standards_Catalogue.xlsx --department ETD --rate-limit 1.5
```

### 3.2 Command-Line Arguments

| Flag | Type | Default | Description |
|---|---|---|---|
| `--input`, `-i` | Path | Required | Path to input BIS department Excel file (`.xlsx`) |
| `--department`, `-d` | String | Required | Technical department code (e.g., `FAD`, `ETD`, `CED`, `MED`) |
| `--cache-only` | Flag | `False` | Strictly parse from local `raw-dir` without making any HTTP requests |
| `--force-reparse` | Flag | `False` | Bypass cache validity check and re-parse all candidate files |
| `--raw-dir` | Path | `data/raw/preview_html` | Directory where raw HTML files are stored and read |
| `--output-dir` | Path | `data/processed/{DEPT}` | Directory where processed JSONL, CSV, and Excel files are written |
| `--rate-limit` | Float | `1.0` | Minimum pause in seconds between live HTTP requests |

---

## 4. BSB Edge Preview URL Mechanics

### 4.1 URL Construction Logic
Official BSB Edge standard preview pages are accessed via:
```text
https://standardsbis.bsbedge.com/Home/Standard_Preview?id={preview_id}
```

### 4.2 Preview ID Derivation Rules
Preview IDs are deterministically derived from the standard designation:

1. **Standard Numbers:**
   - Format: `IS <number> : <year>` → `{number}_{year}`
   - Example: `IS 17873 : 2022` → `17873_2022`
2. **Part Numbers:**
   - Format: `IS <number> (Part <P>) : <year>` → `{number}_{P}_{year}`
   - Example: `IS 1969 (Part 1) : 2018` → `1969_1_2018`
3. **Part and Section Numbers:**
   - Format: `IS <number> (Part <P>/Sec <S>) : <year>` → `{number}_{P}_{S}_{year}`
   - Example: `IS 5887 (Part 8/Sec 1) : 2023` → `5887_8_1_2023`
4. **Candidate Fallback Sequences:**
   When secondary formats exist (e.g. without year or dual-numbered representations), `src/preview_id.py` generates ordered candidate IDs tested sequentially against cache or live endpoints.

---

## 5. Artifact Outputs & Schema Contracts

Each collector execution produces the following atomic artifacts in `data/processed/{DEPARTMENT}/`:

```text
data/processed/{DEPARTMENT}/
├── {DEPT}_standards.jsonl           <- Core hydrated standard records with scope, foreword, notes
├── {DEPT}_references.jsonl          <- Relational edge records (normative, test method, dual-numbered)
├── {DEPT}_source_availability.jsonl <- Data completeness and verification tracking record per standard
├── {DEPT}_source_availability.csv   <- Tabular availability summary for analyst eyeball audit
├── {DEPT}_enriched.xlsx             <- Original Excel catalog augmented with extracted metadata columns
└── state.json                       <- Atomic state tracking resumability, first/last run timestamps
```

And in `data/reports/`:
```text
data/reports/{DEPT}_collection_report.json <- High-level run telemetry, counts, and manifest SHA256
```

---

## 6. Resumability & Atomic State Management

1. **Atomic State File (`state.json`):** State is written to `state.json.tmp` and renamed atomically, preventing state corruption during unexpected process termination.
2. **Run Timestamps:**
   - `first_run_started_at`: Preserved across repeated runs, establishing original provenance baseline.
   - `last_run_started_at`: Updated on every execution, tracking recent pipeline activity.
3. **Idempotent Ingestion:** Re-running the collector over an existing output directory does not duplicate records; canonical designations serve as primary keys.
