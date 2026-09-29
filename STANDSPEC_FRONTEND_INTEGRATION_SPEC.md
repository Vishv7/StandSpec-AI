# StandSpec AI — Frontend Integration Specification & UI/UX Design Context

**Document Version:** 1.0.0  
**Target Design Engine:** Stitch AI / Claude / v0 / Modern Web Studio  
**Target Architecture:** React + Vite + Tailwind CSS + Lucide Icons (Frontend) ⟷ FastAPI Async REST & WebSockets (Backend)  
**Target Domain:** Indian Standards (BIS) Automated Tender Recommendation, Statutory QCO Compliance & Agentic Audit System  

---

## 1. Executive Summary & System Identity

### 1.1 What is StandSpec AI?
**StandSpec AI** is an enterprise-grade, deterministic, and agentic AI decision engine for Indian public and industrial procurement. It ingests free-form procurement queries, tender specifications, and tender PDF documents (e.g., GeM tenders, CPWD tenders, Railways/Defense bids) and automatically determines:
1. **Applicable Indian Standard(s) (IS)** with per-attribute technical grounding (Voltage, Cross-Section, Material, Application, Dimensions, Installation).
2. **Statutory Regulatory Mandate Status**: Confirms whether the item falls under mandatory Quality Control Orders (QCO) or Compulsory Registration Schemes (CRS) issued by Government ministries (e.g., DPIIT, Ministry of Power). Strictly prevents false-negative legal statements.
3. **Temporal Lifecycle Validity**: Detects whether cited or recommended standards are **Current**, **Superseded**, or **Withdrawn** as of a specific evaluation date (e.g., tender publish date or opening date), resolving the exact legally binding edition and amendment.
4. **Agentic Reasoning with Deterministic Safety Veto**: Uses an LLM agent for compositional understanding and multi-step investigation, but subjects every proposal to a strict, hard-coded **Deterministic Safety Validator** that has absolute veto authority to eliminate hallucinations.
5. **Calibrated Selective Abstention**: Unlike generic AI that guesses when information is ambiguous, StandSpec AI formally abstains across 9 strict decision states (e.g., `CLARIFICATION_REQUIRED`, `EXPERT_REVIEW_REQUIRED`, `OUTSIDE_PROTOTYPE_COVERAGE`).

### 1.2 Target Personas
* **Procurement / Tender Officers (Public & Private)**: Need to formulate NIT (Notice Inviting Tender) specifications or verify that received vendor bids conform to latest BIS norms and mandatory QCOs.
* **Tender Evaluation Committee (TEC) Members**: Need to audit bidder compliance matrices against genuine Indian Standards without manual cross-referencing across thousands of PDF gazettes.
* **Suppliers & Bidders**: Need to know the exact IS codes, testing requirements, and marking rules required to qualify for government bids.
* **Compliance & Quality Auditors**: Need complete, mathematically reproducible audit trails with exact clause grounding, tool traces, and legal citations.

---

## 2. End-to-End System Topology

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FRONTEND CLIENT (React)                                │
│                                                                                        │
│  ┌───────────────────────┐  ┌─────────────────────────┐  ┌──────────────────────────┐  │
│  │ 1. Query Studio View  │  │ 2. Tender PDF Studio    │  │ 3. Standards Explorer    │  │
│  │ (Ad-hoc query & chat) │  │ (Clause + Audit Report) │  │ (Knowledge Graph & Spec) │  │
│  └───────────┬───────────┘  └────────────┬────────────┘  └─────────────┬────────────┘  │
│              │                           │                             │               │
│              └───────────────────────────┼─────────────────────────────┘               │
│                                          │                                             │
│                                HTTP REST / WebSocket                                   │
└──────────────────────────────────────────┼─────────────────────────────────────────────┘
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI BACKEND GATEWAY                                   │
│                                                                                        │
│  ┌────────────────────────────┐  ┌──────────────────────────────────────────────────┐  │
│  │  REST API Router           │  │  WebSocket Trace Streamer                        │  │
│  │  /api/v1/query/recommend   │  │  /api/v1/agent/stream (live step/tool streaming) │  │
│  │  /api/v1/tender/upload     │  └──────────────────────────────────────────────────┘  │
│  │  /api/v1/tender/batch      │                                                        │
│  └─────────────┬──────────────┘                                                        │
└────────────────┼───────────────────────────────────────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                            STANDSPEC AI CORE ENGINE LAYER                              │
│                                                                                        │
│  ┌─────────────────────────────┐         ┌──────────────────────────────────────────┐  │
│  │ PDF Ingestion & Chunking    │         │ StandSpecAgent (Agentic Orchestrator)    │  │
│  │ - Text/Table Extractor      │         │ - Understand & Plan (LLM Reasoning)      │  │
│  │ - Clause/BOQ Segmenter      │         │ - 7 BIS Tools (Deterministic Dispatch)   │  │
│  └─────────────┬───────────────┘         │ - Deterministic Safety Validator (Veto)  │  │
│                │                         └────────────────────┬─────────────────────┘  │
│                ▼                                              ▼                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ StandSpecRecommendationEngine                                                    │  │
│  │ 1. ProcurementRequirementExtractor (Grounded entity extraction)                 │  │
│  │ 2. Hybrid Retrieval (BM25 + Dense + RRF + Graph Expansion + Cross-Encoder)      │  │
│  │ 3. Technical Applicability Engine (Per-attribute match / mismatch evaluation)    │  │
│  │ 4. Lifecycle Gate (Temporal edition resolution & amendment tracking)             │  │
│  │ 5. Regulatory Gate (Statutory QCO / CRS Gazette verification)                    │  │
│  │ 6. EvidenceBundle & Claim Policy (Evaluates proof readiness; prevents leaps)     │  │
│  │ 7. Calibrated Abstention Policy (Determines 1 of 9 authoritative states)          │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                           │                                            │
│                                           ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Indexed Knowledge Store & Release Manifest                                      │  │
│  │ - Verified CED & ETD Standards Graph (~10,000+ nodes & relationships)            │  │
│  │ - Gazette QCO Regulatory Corpus & Scopes                                         │  │
│  │ - BM25 Inverted Index & Dense Embeddings                                         │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Frontend Views & UX Requirements for Stitch AI

The frontend is divided into **four primary views**, unified by a persistent institutional header and navigation sidebar.

### 3.1 Global Header & Navigation
* **Institutional Branding**: StandSpec AI logo with badge `v1.2.0 | CED + ETD Verified Edition`.
* **Corpus Scope Tag**: `Coverage: Civil (CED) & Electrotechnical (ETD) Standards`.
* **As-Of Evaluation Date Control**: Global date selector (defaults to current date, configurable for auditing past tenders).
* **System Health Indicator**: Live status pill (`Engine: READY`, `Indexed Nodes: 10,042`, `QCOs: Active`).
* **Theme Mode Switch**: Dark mode (primary/default) and light mode.

---

### 3.2 View 1: Ad-Hoc Procurement Query Studio
This screen is designed for officers writing or testing individual item specifications.

#### Essential Components:
1. **Interactive Query Console**:
   * **Multi-Language Textarea**: Large input with placeholder: *"e.g., Supply of 1.1 kV grade XLPE insulated 3-core 240 sq mm aluminium conductor underground cables conforming to standard specifications..."*
   * **Language Detection Tag**: Live chip showing `Detected: English` (or `Hindi (हिंदी)`, `Gujarati (ગુજરાતી)`, `Hinglish`).
   * **Pre-Baked Query Chips (Quick Testing)**:
     - `1.1 kV XLPE 3-Core Power Cable` (Primary Match Test)
     - `Supply of uPVC pipes as per IS 1180 Part 1` (Standard Mismatch Test)
     - `Supply of Fresh Bananas / Grade A Rice` (Out of Scope Boundary Test)
     - `Supply of 33/11 kV Power Transformers` (High-Voltage Mandatory QCO Test)
     - `Pipes for potable water supply` (Under-specified / Ambiguity Test)
   * **Execution Mode Selector**:
     - `Autonomous Agent (Default)`: Full multi-step reasoning, tool dispatching, and dynamic clarification.
     - `Deterministic Pipeline`: Direct high-speed 9-step pipeline without LLM overhead.
   * **Action Buttons**:
     - `[Analyze & Recommend]` (Primary CTA, glowing gradient).
     - `[Extract Entities Only]` (Instant regex-grounded parser preview).
     - `[Clear]`.

2. **Live Grounded Requirement Breakdown (Accordion / Card)**:
   * Displays extracted entities with character spans and confidence gauges:
     * **Product**: e.g., `Power Cable` (100% confidence, span: `"power cable"`)
     * **Material**: e.g., `XLPE / Aluminium`
     * **Voltage Rating**: e.g., `1.1 kV` (Normalized: `1100 V`)
     * **Dimensions**: e.g., `3-core x 240 sq mm`
     * **Installation / Environment**: e.g., `Underground direct burial`
     * **Missing Discriminators Warning Pill**: e.g., `Missing: Armouring Type (Armoured vs Unarmoured)`

3. **Recommendation & Compliance Dossier (Results Area)**:
   * **Authoritative Decision State Banner**: Full-width prominent alert banner displaying 1 of the 9 states (see Section 4 for visual state matrix).
   * **Primary Recommended Standard Card**:
     - **Standard Designation**: e.g., `IS 7098 (Part 1):1988` (Bold large display, copy button).
     - **Title**: *Specification for Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables: Part 1 For Working Voltages up to and Including 1100 V*.
     - **Claim Level**: `VERIFIED_FOR_RECOMMENDATION` badge (Emerald Green).
     - **Technical Attribute Match Matrix**:
       - ✓ Product: Matched (`Power Cable`)
       - ✓ Voltage: Matched (`Up to 1100 V`)
       - ✓ Material: Matched (`XLPE`)
       - ? Armouring: Unknown (Default standard covers both)
     - **Match Rationale**: Human-readable explanation grounded in BIS clauses.
   * **Statutory Regulatory & Mandate Widget**:
     - **Status Badge**: `STATUTORY MANDATE: MANDATORY` (Shield Icon, Amber/Red alert).
     - **Order Number**: `DPIIT QCO Order S.O. 1234(E)` with verified gazette date.
     - **Legal Disclaimer Note**: Formally notes mandatory certification under Section 16 of the BIS Act, 2016.
   * **Lifecycle & Supersession Timeline**:
     - **Edition Status**: `Active / Current Valid Edition`.
     - **Historical Chain**: `IS 1554 (Part 1) → Superseded by IS 7098 (Part 1) → Latest Reaffirmation: 2020`.
   * **Alternative Standards Drawer**: List of related/allied standards (e.g., `IS 10810` Test Methods, `IS 8130` Conductors) with roles.
   * **Missing Discriminators & Clarification Questions Box** (Triggered if under-specified):
     - Interactive question cards: *"Is this cable meant for overhead aerial bunched application or direct underground burial?"* with clickable answer buttons to re-run with refined context.

4. **Agent Audit & Reasoning Drawer (Collapsible Side Sheet / Modal)**:
   * Step-by-step trace showing:
     - `Step 1 [Plan]`: Formulated search strategy for 1.1 kV XLPE cable.
     - `Step 2 [Tool: search_standards]`: Dispatched BM25 + Dense retrieval. Top 5 candidates retrieved.
     - `Step 3 [Tool: check_applicability]`: Verified IS 7098 Part 1 against 1.1 kV. State: `APPLICABLE`.
     - `Step 4 [Tool: check_lifecycle]`: Verified edition 1988 reaffirmed 2020.
     - `Step 5 [Tool: check_regulatory]`: Dispatched QCO index. Identified mandatory Gazette S.O.
     - `Step 6 [Safety Validator Gate]`: Validated proposal against graph invariants. **PASS**.
   * Latency and token consumption counter.

---

### 3.3 View 2: Tender PDF Document Studio (Hybrid Workflow)
This is the core enterprise feature for uploading tender documents, RFPs, and NITs.

#### The Hybrid User Workflow:
1. **Upload & Ingest**: User drops a PDF tender document (supports 1 to 100+ pages).
2. **Dual-Path Selection**:
   * **Path A: Interactive Clause Workbench** (Granular, clause-by-clause evaluation).
   * **Path B: Full-Document Automated Compliance Audit** (One-click complete tender audit).

#### Essential Components:
1. **PDF Drag-and-Drop Zone**:
   * Accepts `.pdf` files up to 50 MB.
   * Displays upload progress bar, file size, page count, and document metadata extraction.
   * **Tender Metadata Header**: Tender Title, Tender ID, Issuing Authority (e.g., CPWD, NTPC, BHEL), Tender Publish Date.

2. **Path A — Interactive Clause Workbench**:
   * **Left Panel: PDF Previewer**: Interactive document viewer highlighting extracted technical clauses and schedules of quantities.
   * **Right Panel: Extracted Line Items Table**:
     - Table columns:
       - `[ ]` (Multi-select checkbox for batch processing)
       - `Item #` / `Clause Ref` (e.g., `Item 3.1 - Section B`)
       - `Extracted Specification Description` (Editable in-line)
       - `Detected Domain` (`Electrotechnical (ETD)`, `Civil (CED)`, or `Out of Scope`)
       - `Recommended IS Standard` (Status badge or standard number)
       - `Mandatory QCO?` (`Yes [QCO]`, `No`, or `Unverified`)
       - `Lifecycle Alert` (`Current`, `Superseded ⚠`)
       - `Action` (`[Recommend]`, `[Details]`, `[Exclude]`)
     - **Batch Operations Bar**:
       - `[Select All]` | `[Run Batch Recommendation on 14 Selected Items]` | `[Export Selected to Excel]`.

3. **Path B — Full-Document Automated Compliance Audit Dossier**:
   * **Executive Compliance Summary Cards**:
     - **Total Line Items Analyzed**: e.g., `38 Items`.
     - **Full Compliance Score**: e.g., `84% Valid Standards Cited`.
     - **High Risk / Critical Violations Count**: e.g., `3 Violations` (Obsolete standards cited or mandatory QCO missing).
     - **Ambiguous / Incomplete Specs Count**: e.g., `5 Items Requiring Clarification`.
   * **Red-Flag Findings & Compliance Alerts Card**:
     - 🔴 **Superseded Standard Cited in Tender**: Tender cites `IS 1180:1989` (Withdrawn) → System alerts: *Must be updated to IS 1180 (Part 1):2014 or bid is legally vulnerable.*
     - 🔴 **Mandatory QCO Non-Compliance**: Specification for low-voltage switchgear omits mandatory ISI mark certification required under Order 2023.
     - 🟡 **Standard-Product Mismatch**: Tender states *"uPVC pipes conforming to IS 1180 Part 1"* (IS 1180 is for Transformers, not Pipes).
   * **Unified Tender Compliance Matrix Table**:
     - Interactive sortable grid showing every tender item alongside Recommended Standard, Mandate Status, Discrepancies, and Corrective Action.
   * **One-Click Export Center**:
     - `[Download Executive Audit Report (PDF)]`.
     - `[Export Detailed Compliance Matrix (.xlsx)]`.
     - `[Export Tender Amendment / Corrigendum Draft (.docx)]`.

---

### 3.4 View 3: BIS Standards & Knowledge Graph Explorer
For technical officers needing to explore Indian Standards directly.

#### Essential Components:
1. **Fast Search / Filter Bar**: Search by designation (e.g., `IS 7098`), keyword, or Department (`CED` / `ETD`).
2. **Standard Details Sheet**:
   * Header: Designation, Title, Committee (e.g., `ETD 09`), ICS code, Active/Reaffirmation year.
   * Official Scope clause text.
   * Verified Technical Attributes (voltages, materials, conductors, test methods).
   * Allied & Referenced Standards (Part 2, Part 3, testing standards).
   * Mandatory QCO Order details with link to official Gazette notification.
3. **Interactive Hierarchy & Relationship Graph**:
   * Visual node diagram showing base standard, sibling parts, test standards, and superseding standards.

---

## 4. Authoritative Decision States & Color Tokens

StandSpec AI operates with **9 strict, mutually exclusive decision states**. The UI must reflect these states using distinct visual styling, iconography, and user cues:

| State Key | UI Display Name | Color Palette | Icon | Meaning / Required UI Action |
|:---|:---|:---|:---:|:---|
| `PRIMARY_RECOMMENDATION_AVAILABLE` | **Primary Standard Verified** | **Emerald / Green** (`#059669`, `bg-emerald-500/10`) | `CheckCircle2` | A verified, applicable standard is confirmed. Show primary card with full details. |
| `CONDITIONAL_RECOMMENDATION` | **Conditional Recommendation** | **Amber / Gold** (`#D97706`, `bg-amber-500/10`) | `AlertTriangle` | Plausible match, but ground truth scope is thin or minor parameters need verification. |
| `MULTIPLE_POSSIBLE_STANDARDS` | **Multiple Standards Applicable** | **Blue / Indigo** (`#3B82F6`, `bg-blue-500/10`) | `Layers` | Requirements fit multiple distinct standards (e.g., Part 1 vs Part 2). Prompt user to pick. |
| `CLARIFICATION_REQUIRED` | **Specification Clarification Needed** | **Cyan / Sky** (`#0284C7`, `bg-sky-500/10`) | `HelpCircle` | Core technical discriminator is missing (e.g., voltage or pipe diameter). Show questions. |
| `EXPERT_REVIEW_REQUIRED` | **Technical Review Required** | **Orange / Bronze** (`#EA580C`, `bg-orange-500/10`) | `FileSearch` | Standard candidate identified, but authoritative scope evidence is absent in index. |
| `NO_CONFIDENT_MATCH` | **No Confident Match** | **Rose / Red** (`#E11D48`, `bg-rose-500/10`) | `XCircle` | Technical specification does not match any indexed Indian Standard in this domain. |
| `INSUFFICIENT_INFORMATION` | **Insufficient Specifications** | **Slate / Neutral** (`#64748B`, `bg-slate-500/10`) | `Info` | Query is too short or lacks technical nouns to initiate a valid engineering search. |
| `OUTSIDE_PROTOTYPE_COVERAGE` | **Outside Prototype Boundary** | **Purple / Violet** (`#9333EA`, `bg-purple-500/10`) | `ShieldAlert` | Item belongs to domains outside Civil (CED) and Electrical (ETD) (e.g., food, textiles). |
| `STANDARD_DATA_UNAVAILABLE` | **Standard Document Not Indexed** | **Zinc / Gray** (`#71717A`, `bg-zinc-500/10`) | `Database` | Designation is known, but full standard body and tables are not yet ingested. |

---

## 5. Complete Data Contracts & Schema Fields

The frontend must conform to the following backend schemas.

### 5.1 Ad-Hoc Recommendation Request & Response

#### Request: `POST /api/v1/query/recommend`
```json
{
  "query": "Supply of 1.1 kV XLPE insulated three-core 185 sq mm aluminium power cable for underground utility",
  "evaluation_date": "2026-09-30",
  "mode": "auto", 
  "top_k": 5
}
```

#### Response Payload (`AgentFinalAnswer` / `RecommendationResult`):
```json
{
  "query": {
    "raw_text": "Supply of 1.1 kV XLPE insulated three-core 185 sq mm aluminium power cable for underground utility",
    "query_id": "Q_20260930_001",
    "language": "en"
  },
  "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
  "confidence": "HIGH",
  "primary_recommendation": {
    "designation": "IS 7098 (Part 1):1988",
    "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables: Part 1 For Working Voltages up to and Including 1100 V",
    "claim_level": "VERIFIED_FOR_RECOMMENDATION",
    "reason": "Direct technical match for XLPE insulated cable rated up to 1.1 kV (1100 V) with aluminium conductor.",
    "applicability_state": "APPLICABLE",
    "matched_attributes": [
      "product: Power Cable",
      "voltage: 1.1 kV (<= 1100 V)",
      "material: XLPE insulation",
      "conductor: Aluminium",
      "installation: Underground"
    ],
    "evidence_ids": ["BIS_NODE_IS_7098_1_1988"]
  },
  "alternative_standards": [
    {
      "designation": "IS 1554 (Part 1):1988",
      "title": "PVC Insulated (Heavy Duty) Electric Cables: Part 1 For Working Voltages up to and Including 1100 V",
      "reason": "Alternative PVC insulation standard for same 1.1 kV voltage class."
    },
    {
      "designation": "IS 8130:2013",
      "title": "Conductors for Insulated Electric Cables and Flexible Cords",
      "reason": "Mandatory allied component standard specifying conductor resistance and elongation."
    }
  ],
  "review_candidate": null,
  "clarifications_needed": [],
  "normalized_requirements": {
    "product_status": "EXTRACTED",
    "requirements": {
      "product": { "value": "power cable", "normalization": "Power Cable", "confidence": 1.0 },
      "voltage": { "value": "1.1 kV", "normalization": "1.1 kV", "confidence": 0.95 },
      "material": { "value": "XLPE", "normalization": "XLPE", "confidence": 0.98 },
      "dimensions": { "value": "three-core 185 sq mm", "normalization": "3 x 185 sq mm", "confidence": 0.92 },
      "installation": { "value": "underground", "normalization": "underground", "confidence": 0.90 }
    },
    "missing_discriminators": []
  },
  "lifecycle": {
    "state": "ACTIVE",
    "recommended_edition": "IS 7098 (Part 1):1988",
    "superseded_by": null,
    "is_superseded": false,
    "reaffirmation_year": "2020",
    "evidence": ["BIS Published Standards Catalog CED/ETD 2026"]
  },
  "regulatory": {
    "state": "MANDATORY_CONFIRMED",
    "qco_order_number": "DPIIT Order S.O. 4312(E)",
    "gazette_so_number": "S.O. 4312(E)",
    "effective_date": "2021-04-01",
    "statement": "Statutory Mandate: MANDATORY under Gazette Order DPIIT S.O. 4312(E). ISI certification mark compulsory.",
    "evidence": ["Gazette of India Extraordinary Part II Sec 3(ii)"]
  },
  "natural_language_explanation": "For the procurement of 1.1 kV 3-core 185 sq mm XLPE underground cables, the authoritative primary standard is IS 7098 (Part 1):1988. This specification is currently ACTIVE (reaffirmed 2020) and is legally MANDATORY under DPIIT Quality Control Order S.O. 4312(E). Manufacturers must possess a valid BIS license with the ISI mark.",
  "agent_metadata": {
    "execution_mode": "autonomous_agent",
    "step_count": 5,
    "search_rounds": 1,
    "revision_rounds": 0,
    "validator_status": "PASSED",
    "latency_ms": 342
  },
  "tool_calls": [
    {
      "step": 1,
      "tool": "search_standards",
      "arguments": { "query": "1.1 kV XLPE aluminium power cable underground", "top_k": 5 },
      "status": "SUCCESS"
    },
    {
      "step": 2,
      "tool": "check_applicability",
      "arguments": { "designation": "IS 7098 (Part 1):1988" },
      "status": "SUCCESS"
    },
    {
      "step": 3,
      "tool": "check_lifecycle",
      "arguments": { "designation": "IS 7098 (Part 1):1988", "evaluation_date": "2026-09-30" },
      "status": "SUCCESS"
    },
    {
      "step": 4,
      "tool": "check_regulatory",
      "arguments": { "designation": "IS 7098 (Part 1):1988" },
      "status": "SUCCESS"
    }
  ]
}
```

---

### 5.2 Tender PDF Upload & Hybrid Workbench Endpoints

#### 1. Upload & Parse PDF: `POST /api/v1/tender/upload`
* **Request**: `multipart/form-data` with `file: tender_spec.pdf`, `evaluation_date: "2026-09-30"`.
* **Response Payload**:
```json
{
  "document_id": "DOC_20260930_X9A2",
  "filename": "Tender_NIT_Power_Piping_Package_2026.pdf",
  "page_count": 42,
  "tender_metadata": {
    "tender_id": "NIT-2026-NTPC-CIVIL-044",
    "title": "Supply and Laying of Raw Water Pipelines and Auxiliary Power Distribution",
    "issuing_authority": "National Thermal Power Corporation",
    "publish_date": "2026-08-15"
  },
  "total_extracted_clauses": 18,
  "clauses": [
    {
      "item_id": "ITEM_001",
      "clause_reference": "Section 4.2 - Bill of Quantities Sl. No. 1",
      "raw_text": "Supply of centrifugally cast (spun) iron pressure pipes for water, Class LA, nominal diameter 300 mm with rubber gasket joints.",
      "page_number": 14,
      "domain": "Civil Engineering (CED)",
      "extracted_entities": {
        "product": "Cast Iron Pressure Pipes",
        "material": "Centrifugally Cast Iron",
        "dimensions": "DN 300 mm",
        "grade": "Class LA",
        "application": "Water conveyance"
      },
      "initial_recommendation": {
        "designation": "IS 1536:2001",
        "title": "Centrifugally Cast (Spun) Iron Pressure Pipes for Water, Gas and Sewage",
        "lifecycle_state": "ACTIVE",
        "is_mandatory_qco": true,
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE"
      }
    },
    {
      "item_id": "ITEM_002",
      "clause_reference": "Section 4.3 - Technical Spec 12.1",
      "raw_text": "Cables for 415V distribution shall be PVC insulated conforming to IS 1554 Part 1.",
      "page_number": 19,
      "domain": "Electrotechnical (ETD)",
      "extracted_entities": {
        "product": "Power Cable",
        "voltage": "415 V",
        "material": "PVC",
        "cited_standard": "IS 1554 (Part 1)"
      },
      "initial_recommendation": {
        "designation": "IS 1554 (Part 1):1988",
        "title": "PVC Insulated (Heavy Duty) Electric Cables: Part 1",
        "lifecycle_state": "ACTIVE",
        "is_mandatory_qco": true,
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE"
      }
    }
  ]
}
```

#### 2. Run Batch Recommendation: `POST /api/v1/tender/batch-recommend`
* **Request**:
```json
{
  "document_id": "DOC_20260930_X9A2",
  "item_ids": ["ITEM_001", "ITEM_002"]
}
```
* **Response**: Array of detailed `RecommendationResult` objects matched by `item_id`.

#### 3. Full-Document Audit Report: `GET /api/v1/tender/{doc_id}/report`
* **Response**: Complete aggregated report structure containing:
  * `executive_summary`: total items, compliance percentage, critical alerts count.
  * `discrepancies`: items where tender cited superseded standards, mismatched standards, or non-QCO specs.
  * `compliance_matrix`: complete array of all line items with cross-verified BIS standards.
  * `download_urls`: links to `.pdf` and `.xlsx` generated exports.

---

### 5.3 Real-Time Agent WebSocket: `WS /api/v1/agent/stream`
* **Purpose**: Streams live reasoning, tool executions, and validator verdicts to the UI in real time.
* **Message Frames**:
```json
{"event": "agent_start", "query": "...", "timestamp": 1727650000}
{"event": "thought", "text": "Analyzing technical requirements: Detected 1.1 kV XLPE cable..."}
{"event": "tool_call_start", "tool": "search_standards", "arguments": {"query": "..."}}
{"event": "tool_call_finish", "tool": "search_standards", "result_count": 5, "top_candidate": "IS 7098 (Part 1):1988"}
{"event": "tool_call_start", "tool": "check_regulatory", "arguments": {"designation": "IS 7098 (Part 1):1988"}}
{"event": "tool_call_finish", "tool": "check_regulatory", "status": "MANDATORY_CONFIRMED", "qco": "DPIIT S.O. 4312(E)"}
{"event": "validator_verdict", "status": "PASSED", "message": "Proposal adheres to graph invariants and evidence rules."}
{"event": "agent_finish", "final_answer": { ... }}
```

---

## 6. Stitch AI Design Prompt Kit & UI Tokens

Use the following curated styling tokens and prompt snippets directly in **Stitch AI** or v0 to generate high-fidelity components.

### 6.1 Design Tokens (Tailwind CSS)

```css
/* Color Palette: Institutional Authority + Modern Glassmorphism */
:root {
  --bg-primary: #0b0f19;       /* Deep Slate / Charcoal base */
  --bg-secondary: #111827;     /* Card surface */
  --bg-tertiary: #1f2937;      /* Hover surface & borders */
  --border-subtle: #374151;    /* Subtle dividers */
  --accent-gold: #f59e0b;      /* BIS Seal Gold / Institutional authority */
  --accent-blue: #3b82f6;      /* Tech blue for links & action */
  
  /* Semantic Status Colors */
  --state-verified: #10b981;   /* Emerald Green: PRIMARY_RECOMMENDATION_AVAILABLE */
  --state-conditional: #f59e0b;/* Amber: CONDITIONAL_RECOMMENDATION */
  --state-multiple: #6366f1;   /* Indigo: MULTIPLE_POSSIBLE_STANDARDS */
  --state-clarify: #06b6d4;    /* Cyan: CLARIFICATION_REQUIRED */
  --state-review: #f97316;     /* Orange: EXPERT_REVIEW_REQUIRED */
  --state-abstain: #ef4444;    /* Red: NO_CONFIDENT_MATCH / REJECTED */
  --state-outside: #a855f7;    /* Purple: OUTSIDE_PROTOTYPE_COVERAGE */
}
```

### 6.2 Master Prompt for Stitch AI: "Procurement Query Studio"
```text
Design a hyper-modern, institutional AI web dashboard for "StandSpec AI" - an Indian Standards (BIS) Procurement & Tender Decision Engine.

Theme: Dark mode (Deep Slate #0B0F19 background, glassmorphism cards with #1F2937 borders, gold #F59E0B and emerald #10B981 accents). Modern typography using Inter and JetBrains Mono for code/standards designations.

Header:
- Left: Logo "StandSpec AI" with a glowing shield badge "v1.2.0 | CED & ETD".
- Center: Global Date Picker labeled "Evaluation As-Of Date" defaulting to "Today (30 Sep 2026)" with a calendar icon.
- Right: System health indicator "Engine: Online (10,042 Standards)" and theme toggle.

Main Content (Two-Column Layout):
Left Column (Input & Extraction, 45% width):
- Top Card: "Procurement Specification Query"
  - Large textarea with prompt chips underneath: "1.1 kV XLPE Power Cable", "IS 1180 Transformers", "uPVC Potable Water Pipes".
  - Mode toggle: [Autonomous Agent (Live Reasoning)] vs [Deterministic Fast Pipeline].
  - Primary button: "Analyze & Verify Standard" with subtle pulse glow.
- Bottom Card: "Extracted Technical Requirements"
  - Collapsible card showing grounded tags: Product ("Power Cable"), Material ("XLPE"), Voltage ("1.1 kV"), Conductor ("Aluminium").
  - Warning tag if attributes are missing: "Missing Discriminator: Armouring Type".

Right Column (Decision & Compliance Dossier, 55% width):
- Top Banner: Authoritative Decision Banner in Emerald Green:
  - Big badge: "PRIMARY RECOMMENDATION AVAILABLE"
  - Subtitle: "Standard fully verified against CED/ETD corpus with mandatory regulatory backing."
- Core Recommendation Card:
  - Standard Designation: "IS 7098 (Part 1):1988" (large mono font with copy icon and external BIS link).
  - Title: "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables..."
  - Claim Level: "VERIFIED_FOR_RECOMMENDATION" (Green pill).
  - 2-Column Grid of Matched Specifications:
    - Left: Tender Requirement (e.g., "1.1 kV working voltage", "Underground duty").
    - Right: Standard Clause Match (e.g., "Clause 4.1 Verified", "Table 2 Compliant").
- Statutory QCO Card (Amber border):
  - Shield Icon + "STATUTORY MANDATE: MANDATORY"
  - Text: "DPIIT Quality Control Order S.O. 4312(E). ISI Certification Mark is legally compulsory for public procurement."
- Supersession Timeline:
  - Mini horizontal stepper: IS 1554:1988 (Old) -> IS 7098 Part 1 (Current Active, Reaffirmed 2020).
- Action Footer:
  - Button "View Real-Time Agent Audit Trace" (opens side drawer with step-by-step tool calls).
  - Button "Download Compliance Certificate (.pdf)".
```

### 6.3 Master Prompt for Stitch AI: "Tender PDF Document Studio"
```text
Design the "Tender PDF Upload & Compliance Studio" for StandSpec AI.

Theme: Dark mode enterprise document intelligence interface. Clean split-view layout.

Top Header Bar:
- Breadcrumb: Tenders / Upload & Audit
- Document Info Bar: Filename "Tender_NIT_Power_Piping_Package_2026.pdf", Size "12.4 MB", "42 Pages", Tender ID "NIT-2026-NTPC-044".
- Segmented View Switcher:
  - [View A: Interactive Clause Workbench]
  - [View B: Full-Document Compliance Audit Report]

View A (Interactive Clause Workbench):
- Left 40%: Document PDF Viewer
  - Interactive PDF preview showing the tender page with highlighted yellow boxes over technical specification paragraphs.
  - Page navigation controls (Page 14 of 42).
- Right 60%: Extracted Line-Items Table
  - Filter bar: Filter by Domain (Civil, Electrical, All), Compliance State (Verified, Action Required), Search text.
  - Table Columns:
    - [x] Checkbox
    - Item / Clause (e.g., "Clause 4.2 - Spun Iron Pipes")
    - Detected Spec & Parameters (e.g., "DN 300 mm Class LA Water Pipe")
    - Recommended BIS Standard (e.g., "IS 1536:2001 [Active]")
    - Mandate Pill ("MANDATORY QCO" in amber)
    - Action ("View Dossier", "Edit Spec")
  - Batch Action Floating Bar at Bottom: "3 Items Selected" -> [Run Batch Recommendation] [Export to Excel].

View B (Full-Document Compliance Audit Report):
- Executive Metric Cards (4 cards in a row):
  - Card 1: Total Line Items (38 Items)
  - Card 2: Standards Compliance Score (84% - Circular Progress Ring)
  - Card 3: Critical Violations (3 - Red Alert Badge)
  - Card 4: Under-specified Items (5 - Cyan Warning Badge)
- Red-Flag Alert Section:
  - Red Alert Card 1: "Superseded Standard Cited: Tender references IS 1180:1989 (Withdrawn). Must require IS 1180 (Part 1):2014."
  - Amber Alert Card 2: "Mandatory QCO Missing: Item 14 lacks mandatory ISI marking stipulation."
- Full Compliance Grid:
  - Detailed spreadsheet-style view with export buttons: [Export PDF Audit Report], [Export GeM Compliance Sheet], [Draft Corrigendum Notice].
```

---

## 7. Implementation Roadmap & Milestones

1. **Phase 1: Backend FastAPI Server Setup** (`src/api/`):
   * Create `src/api/server.py` wrapping `StandSpecAgent` and `StandSpecRecommendationEngine`.
   * Add `pypdf` / `pdfplumber` pipeline for tender PDF text extraction and clause parsing.
   * Implement endpoints: `/api/v1/query/recommend`, `/api/v1/tender/upload`, `/api/v1/tender/batch-recommend`, `/api/v1/agent/stream`.
2. **Phase 2: Stitch AI Frontend Generation**:
   * Generate UI screens using the Stitch AI prompts in Section 6.
   * Review layout against the 9 decision states and color tokens.
3. **Phase 3: Frontend Client Integration**:
   * Wire React components to FastAPI endpoints via Axios / TanStack Query.
   * Connect WebSocket for streaming live agent thoughts and tool calls into the reasoning drawer.
4. **Phase 4: End-to-End Verification & Validation**:
   * Verify ad-hoc query flows with sample benchmarks.
   * Verify PDF upload with sample real-world tender specifications (e.g. electrical cables, transformers, cast iron pipes).
   * Validate that all 9 decision states, QCO disclaimers, and supersession chains render accurately without UI breakage.
