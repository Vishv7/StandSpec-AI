# KNOWLEDGE_BASE_CONTRACTS.md — Data Contracts, Schemas, and Provenance Reference
## StandSpec AI — Layer 1 (Collector) and Layer 2 (Knowledge Base) Semantic Specifications

---

## 1. Executive Overview

This document specifies the exact JSON schemas, relational graph taxonomies, edge obligation semantics, and evidence provenance contracts governing the StandSpec AI knowledge base. Every component in the pipeline must strictly produce and consume records adhering to these specifications.

---

## 2. Canonical Relationship Taxonomy (15 Types)

The StandSpec AI standards knowledge graph (`standards_graph.json`) permits **exactly 15 canonical relationship types** (`CANONICAL_RELATIONSHIP_TYPES` in `src/parser.py`). Arbitrary relationship names are prohibited.

### 2.1 Normative & Reference Clause Types
1. **`normative_reference`**: Standard cited in Section 2 (Normative References) as an indispensable requirement for applying the standard.
2. **`test_method`**: Standard prescribing the test method or procedure for compliance verification (e.g. "tested in accordance with IS 10810").
3. **`measurement_method`**: Standard prescribing measurement methods or procedures.
4. **`calculation_method`**: Standard prescribing calculation formulae, thermal ratings, or mathematical methods.
5. **`terminology_reference`**: Standard providing definitions, symbols, or vocabulary.
6. **`material_reference`**: Standard specifying raw material, compounding, or metallurgical requirements.
7. **`safety_reference`**: Standard prescribing essential safety requirements or fire safety ratings.
8. **`installation_reference`**: Standard prescribing installation, erection, laying, or maintenance procedures.

### 2.2 Conjunction & Adoption Types
9. **`used_in_conjunction_with`**: Standard explicitly mandated to be applied together with another (e.g., "shall be read in conjunction with IS 302 (Part 1)").
10. **`dual_numbering`**: Structural adoption of an international standard under an identical BIS designation (e.g., `IS 18319:2024 / ISO 17665:2024`).
11. **`equivalent_to`**: Technically identical to an international standard, confirmed by explicit textual declaration ("is identical to").
12. **`based_on`**: Formulated on the basis of an international standard without full identity.

### 2.3 Lifecycle & Fallback Types
13. **`supersedes`**: Replaces an older standard (e.g., IS 694:2010 supersedes IS 694:1990).
14. **`superseded_by`**: Standard that has been replaced by a newer edition.
15. **`related_to`**: Explicit fallback for allied technical relationships that cannot be structurally or textually classified with higher confidence.

> [!CAUTION]
> **Taxonomy Rule:** `dual_numbering` is a structural adoption relationship and must **never** be silently converted to `equivalent_to`. Equivalence requires explicit prose evidence.

---

## 3. Obligation Semantics vs. Regulatory Law

> [!IMPORTANT]
> ### Normative Clause Dependency vs Statutory Legal Mandate
> **`relationship_obligation`** on graph edges represents **standard-to-standard normative clause dependency** (i.e. whether standard A normatively requires standard B to be executed).  
> It does **NOT** represent statutory Quality Control Order (QCO) legal mandates.
> - **MANDATORY**: The citing standard contains normative requirements that cannot be fulfilled without adhering to the target standard.
> - **CONDITIONAL**: Required only under specific user-specified conditions (e.g., "if specified by the purchaser", "when required for outdoor duty").
> - **INFORMATIVE**: Provided for guidance, information, or context (e.g., informative annexes, terminology, dual numbering).
> - **RELATED**: Subject-matter proximity without direct clause dependency.
>
> Statutory enforcement (mandatory QCO, Compulsory Registration Scheme, Hallmarking) is governed strictly by the **Regulatory Mandate Layer**, not the technical reference graph.

---

## 4. Edge Verification Status Taxonomy

Every graph edge carries explicit verification provenance:

| Status | Meaning | Conditions |
|---|---|---|
| `VERIFIED` | Full identity confirmed against external manifest | Extracted from a preview page that matched requested department Excel standard designation and version. |
| `SELF_IDENTIFIED_ONLY` | Page self-identifies but has not been checked against an external manifest | Extracted during a raw unanchored HTML directory scan where no requested Excel manifest was supplied. |
| `UNRESOLVED` | Standard designation could not be verified | Header or version mismatch between requested input and preview content. |

---

## 5. Standard Record Schema (`{DEPT}_standards.jsonl`)

```json
{
  "schema_version": "1.2",
  "standard_designation": "IS 17873:2022",
  "original_standard_number": "IS 17873 : 2022",
  "title": "Cotton Yoga Mat - Specification",
  "header_text": "IS 17873 : 2022 Cotton Yoga Mat - Specification",
  "department": "FAD",
  "technical_committee": "FAD 26",
  "ics_raw": "ICS 59.080.60, 97.220.01",
  "ics_codes": ["59.080.60", "97.220.01"],
  "scope": {
    "text": "This standard covers the requirements of yoga mats made of cotton.",
    "status": "present",
    "extraction_method": "html_section",
    "scope_source_section": "SCOPE"
  },
  "national_foreword": {
    "text": null,
    "status": "absent",
    "extraction_method": null
  },
  "notes": {
    "items": [],
    "status": "absent",
    "extraction_method": null
  },
  "references_status": "parsed",
  "references_count": 20,
  "source": {
    "preview_url": "https://standardsbis.bsbedge.com/Home/Standard_Preview?id=17873_2022",
    "verified_source_url": "https://standardsbis.bsbedge.com/Home/Standard_Preview?id=17873_2022",
    "identity_match": "match_version_verified"
  },
  "primary_status": "success",
  "quality": {
    "manual_review_required": false,
    "warnings": [],
    "errors": []
  }
}
```

---

## 6. Reference Edge Schema (`{DEPT}_references.jsonl`)

```json
{
  "source_standard": "IS 17873:2022",
  "target": {
    "designation": "IS 1070:1992",
    "family": "IS",
    "base_number": "1070",
    "part": null,
    "section": null,
    "year": "1992"
  },
  "title": "Reagent grade water - Specification (third revision)",
  "reference_type": "formal_reference",
  "relationship": "normative_reference",
  "relationship_obligation": "MANDATORY",
  "relationship_confidence": "structural",
  "confidence": 1.0,
  "section": "REFERENCES",
  "evidence": {
    "text": "1070 : 1992 Reagent grade water - Specification (third revision)",
    "source_section": "REFERENCES",
    "extraction_method": "html_paragraph",
    "complete": true,
    "continuation_resolved": false,
    "bare_number_resolved": true,
    "table_index": null,
    "row_index": null,
    "column_name": null,
    "sentence_text": null
  },
  "edge_verification_status": "VERIFIED",
  "page_self_identified": true,
  "manifest_identity_verified": true
}
```

---

## 7. Zero-Fabrication Integrity Policy

1. **No Imputation of Absent Fields:** When a preview page lacks a dedicated Scope or Notes section, the collector records `text: null` with `status: "absent"`.
2. **Provenance Traceability:** Every extracted reference carries verbatim `evidence.text` recording the raw character sequence found in the source document.
3. **Continuation Tracking:** Multi-row table reference splits record `continuation_resolved: true` with the parent base standard explicitly tracked.
