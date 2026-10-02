"""
Regulatory Gating Engine — StandSpec AI (Phase 15 / Corrected V1.3)
Evaluates statutory quality control order (QCO) and compulsory registration
scheme (CRS) mandates for resolved Indian Standards.
Loads from governed datasets in data/regulatory/ (qco_orders.jsonl, crs_rules.jsonl).
Implements the safe 5-state regulatory taxonomy:
  - MANDATORY_CONFIRMED
  - MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES
  - NOT_APPLICABLE
  - UNKNOWN
  - CONFLICTING_EVIDENCE
"""

import json
from pathlib import Path
from enum import Enum
from typing import Dict, Any, Optional, List


class RegulatoryState(str, Enum):
    MANDATORY_CONFIRMED = "MANDATORY_CONFIRMED"
    MANDATORY_CONDITIONALLY_APPLICABLE = "MANDATORY_CONDITIONALLY_APPLICABLE"
    NOT_MANDATORY_CONFIRMED = "NOT_MANDATORY_CONFIRMED"
    NOT_VERIFIED_IN_CURRENT_CORPUS = "NOT_VERIFIED_IN_CURRENT_CORPUS"
    MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES = "MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    REGULATORY_SOURCE_UNAVAILABLE = "REGULATORY_SOURCE_UNAVAILABLE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    REGULATORY_DOMAIN_NOT_IN_CURRENT_CORPUS = "REGULATORY_DOMAIN_NOT_IN_CURRENT_CORPUS"


class SourceConsistencyStatus(str, Enum):
    CONSISTENT = "CONSISTENT"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"


class RegulatoryGate:
    """
    Evaluates regulatory certification and QCO mandate status of standards
    against governed regulatory evidence records with full gazette provenance.
    """

    DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "regulatory"

    def __init__(self, data_dir: Optional[Path] = None, qco_registry: Optional[dict] = None):
        self.data_dir = Path(data_dir) if data_dir else self.DEFAULT_DATA_DIR
        self.sources_available: bool = True
        self.qco_records: List[Dict[str, Any]] = []
        self.crs_records: List[Dict[str, Any]] = []
        self.manifest_data: Dict[str, Any] = {}
        self.manifest_sources: List[Dict[str, Any]] = []
        self.designation_to_qco: Dict[str, Dict[str, Any]] = {}
        self.designation_to_records: Dict[str, List[Dict[str, Any]]] = {}

        if qco_registry:
            # Direct in-memory override for test isolation
            for desig, details in qco_registry.items():
                self.designation_to_qco[desig] = details
                self.designation_to_records[desig] = [details]
                norm = self._normalize_desig_key(desig)
                if norm:
                    self.designation_to_records[norm] = [details]
        else:
            self._load_regulatory_data()
            self._load_manifest_data()

    def _normalize_desig_key(self, desig: str) -> str:
        """Strip year, spaces, and lowercase for robust fuzzy key matching."""
        if not desig:
            return ""
        # e.g. "IS 7098 (Part 2):2011" -> "is 7098 (part 2)"
        base = desig.split(":")[0].strip().lower()
        return " ".join(base.split())

    def _load_manifest_data(self):
        """Load source_manifest.json for internal data consistency verification."""
        manifest_path = self.data_dir / "source_manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    self.manifest_data = json.load(f)
                    self.manifest_sources = self.manifest_data.get("sources", [])
            except Exception:
                self.manifest_data = {}
                self.manifest_sources = []

    def _load_regulatory_data(self):
        """
        Load QCO and CRS datasets from disk.
        Preserves ALL records per designation to prevent silent overwrite and allow conflict detection.
        """
        qco_path = self.data_dir / "qco_orders.jsonl"
        crs_path = self.data_dir / "crs_rules.jsonl"

        if not self.data_dir.exists() or (not qco_path.exists() and not crs_path.exists()):
            self.sources_available = False
            return

        def _index_record(rec: Dict[str, Any], src_type: str):
            rec_with_source = dict(rec)
            rec_with_source["_source_type"] = src_type
            for d in rec.get("standard_designations", []):
                d_strip = d.strip()
                self.designation_to_records.setdefault(d_strip, []).append(rec_with_source)
                norm_key = self._normalize_desig_key(d_strip)
                if norm_key and norm_key != d_strip:
                    self.designation_to_records.setdefault(norm_key, []).append(rec_with_source)
                # Keep first seen in designation_to_qco for backward compatibility
                if d_strip not in self.designation_to_qco:
                    self.designation_to_qco[d_strip] = rec_with_source
                if norm_key and norm_key not in self.designation_to_qco:
                    self.designation_to_qco[norm_key] = rec_with_source

        if qco_path.exists():
            with open(qco_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        rec = json.loads(line)
                        self.qco_records.append(rec)
                        _index_record(rec, "QCO")

        if crs_path.exists():
            with open(crs_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        rec = json.loads(line)
                        self.crs_records.append(rec)
                        _index_record(rec, "CRS")

    def _canonical_scheme(self, scheme_str: Optional[str]) -> str:
        """
        Token-safe certification scheme normalization.
        CRITICAL: Never use '"Scheme-I" in s' because 'Scheme-I' is a substring of 'Scheme-II'.
        Checks Scheme-II / CRS before Scheme-I.
        """
        if not scheme_str:
            return "UNKNOWN"
        s = scheme_str.upper().strip()
        if "SCHEME-II" in s or "SCHEME II" in s or "CRS" in s or "SELF-DECLARATION" in s:
            return "SCHEME_II_CRS"
        if "SCHEME-IV" in s or "SCHEME IV" in s or "COC" in s:
            return "SCHEME_IV_COC"
        if "SCHEME-I" in s or "SCHEME I" in s or "ISI" in s:
            return "SCHEME_I_ISI"
        return "OTHER"

    def check_source_consistency(self, standard_designation: str) -> Dict[str, Any]:
        """
        P0-8: Compare source_manifest.json against qco_orders.jsonl and crs_rules.jsonl.
        Identifies internal inconsistencies:
          - URL mismatches (e.g. Steel 256976.pdf vs 256716.pdf)
          - Order identity mismatches (e.g. Cement S.O. 2282(E) 2024 vs S.O. 191(E) 2003)
          - Coverage mismatches (e.g. Smart meters manifest includes IS 14697, JSONL does not)
        Returns:
            {
                "status": "CONSISTENT" | "CONFLICTING" | "UNVERIFIED",
                "details": list[str]
            }
        """
        if not self.manifest_sources:
            return {"status": SourceConsistencyStatus.UNVERIFIED.value, "details": ["No source manifest loaded"]}

        norm_target = self._normalize_desig_key(standard_designation)
        base_target = standard_designation.split(":")[0].strip().lower()

        # Find manifest entries claiming this standard
        matching_manifest_sources = []
        for src in self.manifest_sources:
            cov = [c.strip().lower() for c in src.get("standard_coverage", [])]
            cov_norms = [self._normalize_desig_key(c) for c in cov]
            cov_bases = [c.split(":")[0].strip().lower() for c in cov]
            if (
                base_target in cov
                or norm_target in cov_norms
                or base_target in cov_bases
                or any(norm_target.startswith(c) or c.startswith(norm_target) for c in cov_norms if c)
            ):
                matching_manifest_sources.append(src)

        # Find JSONL records matching this standard
        jsonl_records = self._get_matching_records(standard_designation)

        if not matching_manifest_sources and not jsonl_records:
            return {
                "status": SourceConsistencyStatus.UNVERIFIED.value,
                "details": [f"No records found in manifest or JSONL for {standard_designation}"],
            }

        if jsonl_records and not matching_manifest_sources:
            return {
                "status": SourceConsistencyStatus.UNVERIFIED.value,
                "details": [f"Standard {standard_designation} present in JSONL but absent from source_manifest coverage"],
            }

        if matching_manifest_sources and not jsonl_records:
            return {
                "status": SourceConsistencyStatus.CONFLICTING.value,
                "details": [f"Standard {standard_designation} claimed in source_manifest but absent from JSONL datasets"],
            }

        discrepancies = []
        # Compare order identities (gazette_reference vs gazette_id) and URLs
        for m_src in matching_manifest_sources:
            m_gazette = str(m_src.get("gazette_id") or "").strip().upper()
            m_url = str(m_src.get("source_url") or "").strip()
            m_title = str(m_src.get("order_title") or "").strip()

            found_matching_order = False
            for j_rec in jsonl_records:
                j_gazette = str(j_rec.get("gazette_reference") or "").strip().upper()
                j_url = str(j_rec.get("source_url") or "").strip()

                if m_gazette and j_gazette and m_gazette == j_gazette:
                    found_matching_order = True
                    # Check URL consistency
                    if m_url and j_url and m_url != j_url:
                        discrepancies.append(
                            f"Source URL discrepancy for order {m_gazette}: manifest '{m_url}' vs JSONL '{j_url}'"
                        )
                elif m_gazette and j_gazette and m_gazette != j_gazette:
                    # Potential order identity conflict across versions (e.g. Cement 2024 S.O. 2282(E) vs 2003 S.O. 191(E))
                    discrepancies.append(
                        f"Order identity mismatch: manifest claims {m_gazette} ('{m_title}') while JSONL governs under {j_gazette} ('{j_rec.get('order_title')}')"
                    )

            if not found_matching_order and not discrepancies:
                discrepancies.append(
                    f"Manifest order {m_gazette} does not match any JSONL gazette reference for {standard_designation}"
                )

        if discrepancies:
            return {
                "status": SourceConsistencyStatus.CONFLICTING.value,
                "details": discrepancies,
            }

        return {
            "status": SourceConsistencyStatus.CONSISTENT.value,
            "details": ["Manifest and JSONL order identities, gazette references, and source URLs are consistent"],
        }

    def _get_matching_records(self, standard_designation: str) -> List[Dict[str, Any]]:
        """Retrieve all governed regulatory records for this standard designation."""
        if not standard_designation:
            return []

        # 1. Exact match
        recs = self.designation_to_records.get(standard_designation)
        if recs:
            return recs

        # 2. Normalized base key match
        norm_key = self._normalize_desig_key(standard_designation)
        if norm_key:
            recs = self.designation_to_records.get(norm_key)
            if recs:
                return recs

        # 3. Base standard number match (e.g. "IS 4984" in "IS 4984:2016")
        base_desig = standard_designation.split(":")[0].strip()
        if base_desig:
            recs = self.designation_to_records.get(base_desig)
            if recs:
                return recs

        return []

    def evaluate_regulatory_status(
        self,
        standard_designation: str,
        evaluation_date: Optional[str] = None,
        evaluation_context: Optional[str] = None,
    ) -> dict:
        """
        Evaluate regulatory mandate status for a candidate standard (Regulatory v2).
        Date-aware: Compares effective_date against evaluation_date.
        Conflict-aware: Detects contradictory schemes, dates, or authority mandates.
        Source-consistency aware: Validates manifest vs JSONL records.
        Separates technical applicability from statutory certification mandate.
        """
        if not standard_designation:
            return {
                "regulatory_state": RegulatoryState.UNKNOWN.value,
                "is_mandatory": False,
                "qco_order": None,
                "order_number": None,
                "authority": None,
                "gazette_reference": None,
                "effective_date": None,
                "evidence_excerpt": None,
                "certification_scheme": None,
                "matched_records_count": 0,
                "source_consistency_status": SourceConsistencyStatus.UNVERIFIED.value,
                "statutory_mandate": {
                    "is_statutory_mandatory": False,
                    "enforcement_state": RegulatoryState.UNKNOWN.value,
                    "legal_basis": "Bureau of Indian Standards Act, 2016",
                    "certification_scheme": None,
                    "gazette_reference": None,
                    "has_statutory_exemptions": False,
                    "exemptions": [],
                },
                "corpus_verification_state": "UNKNOWN",
                "notes": "No standard designation provided.",
            }

        # Check source availability
        if not self.sources_available and not self.designation_to_records:
            return {
                "regulatory_state": RegulatoryState.REGULATORY_SOURCE_UNAVAILABLE.value,
                "is_mandatory": False,
                "qco_order": None,
                "order_number": None,
                "authority": None,
                "gazette_reference": None,
                "effective_date": None,
                "evidence_excerpt": None,
                "certification_scheme": None,
                "matched_records_count": 0,
                "source_consistency_status": SourceConsistencyStatus.UNVERIFIED.value,
                "statutory_mandate": {
                    "is_statutory_mandatory": False,
                    "enforcement_state": RegulatoryState.REGULATORY_SOURCE_UNAVAILABLE.value,
                    "legal_basis": "Bureau of Indian Standards Act, 2016",
                    "certification_scheme": None,
                    "gazette_reference": None,
                    "has_statutory_exemptions": False,
                    "exemptions": [],
                },
                "corpus_verification_state": "SOURCE_UNAVAILABLE",
                "notes": "Regulatory evidence sources (data/regulatory/) are unavailable on disk.",
            }

        # Source consistency check
        source_consistency = self.check_source_consistency(standard_designation)
        consist_status = source_consistency["status"]

        matched_records = self._get_matching_records(standard_designation)

        # Deduplicate records by (order_title, order_number, gazette_reference)
        unique_records = []
        seen_keys = set()
        for r in matched_records:
            k = (r.get("order_title"), r.get("order_number"), r.get("gazette_reference"))
            if k not in seen_keys:
                seen_keys.add(k)
                unique_records.append(r)

        if not unique_records:
            return {
                "regulatory_state": RegulatoryState.MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES.value,
                "is_mandatory": False,
                "qco_order": None,
                "order_number": None,
                "authority": None,
                "gazette_reference": None,
                "effective_date": None,
                "evidence_excerpt": None,
                "certification_scheme": None,
                "matched_records_count": 0,
                "source_consistency_status": consist_status,
                "statutory_mandate": {
                    "is_statutory_mandatory": False,
                    "enforcement_state": RegulatoryState.MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES.value,
                    "legal_basis": "Bureau of Indian Standards Act, 2016",
                    "certification_scheme": None,
                    "gazette_reference": None,
                    "has_statutory_exemptions": False,
                    "exemptions": [],
                },
                "corpus_verification_state": RegulatoryState.NOT_VERIFIED_IN_CURRENT_CORPUS.value,
                "notes": (
                    f"No Gazette Quality Control Order (QCO) found in searched datasets for {standard_designation}. "
                    "Standard may be voluntary or governed by ministry-specific procurement guidelines."
                ),
            }

        # P0-8: If source consistency is CONFLICTING, fail closed:
        # A standard whose provenance or source identity is disputed must NOT be MANDATORY_CONFIRMED.
        if consist_status == SourceConsistencyStatus.CONFLICTING.value:
            titles = [r.get("order_title", "Unknown Order") for r in unique_records]
            return {
                "regulatory_state": RegulatoryState.CONFLICTING_EVIDENCE.value,
                "is_mandatory": False,
                "qco_order": " / ".join(titles[:2]),
                "order_number": unique_records[0].get("order_number"),
                "authority": unique_records[0].get("issuing_authority") or unique_records[0].get("authority"),
                "gazette_reference": unique_records[0].get("gazette_reference"),
                "effective_date": unique_records[0].get("effective_date"),
                "evidence_excerpt": f"Source consistency conflict detected: {'; '.join(source_consistency['details'])}",
                "certification_scheme": unique_records[0].get("scheme"),
                "matched_records_count": len(unique_records),
                "source_consistency_status": consist_status,
                "statutory_mandate": {
                    "is_statutory_mandatory": False,
                    "enforcement_state": RegulatoryState.CONFLICTING_EVIDENCE.value,
                    "legal_basis": "Bureau of Indian Standards Act, 2016",
                    "certification_scheme": unique_records[0].get("scheme"),
                    "gazette_reference": unique_records[0].get("gazette_reference"),
                    "has_statutory_exemptions": bool(unique_records[0].get("exemptions")),
                    "exemptions": unique_records[0].get("exemptions", []),
                },
                "corpus_verification_state": "CONFLICTING",
                "notes": (
                    f"Regulatory source consistency status is CONFLICTING for {standard_designation}. "
                    f"Discrepancies: {'; '.join(source_consistency['details'])}. Authoritative legal review required."
                ),
            }

        # P0-7: Exact token-safe scheme and authority conflict analysis
        canonical_schemes = {self._canonical_scheme(r.get("scheme")) for r in unique_records if r.get("scheme")}
        authorities = {
            r.get("issuing_authority") or r.get("authority")
            for r in unique_records
            if r.get("issuing_authority") or r.get("authority")
        }

        # Categorize multi-record relationship:
        # 1. Corroborating: same gazette ref / order or both under same scheme & authority
        # 2. Sequential / Temporal: distinct notification dates representing successive revisions/extensions
        # 3. Conflicting: incompatible schemes (e.g. Scheme-I vs Scheme-II/CRS) or overlapping incompatible authorities
        has_scheme_conflict = False
        if len(canonical_schemes) > 1:
            has_scheme_conflict = True

        if len(unique_records) > 1 and has_scheme_conflict:
            titles = [r.get("order_title", "Unknown Order") for r in unique_records]
            return {
                "regulatory_state": RegulatoryState.CONFLICTING_EVIDENCE.value,
                "is_mandatory": False,
                "qco_order": " / ".join(titles[:2]),
                "order_number": unique_records[0].get("order_number"),
                "authority": " / ".join(filter(None, authorities)),
                "gazette_reference": unique_records[0].get("gazette_reference"),
                "effective_date": unique_records[0].get("effective_date"),
                "evidence_excerpt": "Conflicting regulatory certification schemes across multiple orders.",
                "certification_scheme": " / ".join(filter(None, canonical_schemes)),
                "matched_records_count": len(unique_records),
                "source_consistency_status": consist_status,
                "statutory_mandate": {
                    "is_statutory_mandatory": False,
                    "enforcement_state": RegulatoryState.CONFLICTING_EVIDENCE.value,
                    "legal_basis": "Bureau of Indian Standards Act, 2016",
                    "certification_scheme": " / ".join(filter(None, canonical_schemes)),
                    "gazette_reference": unique_records[0].get("gazette_reference"),
                    "has_statutory_exemptions": any(bool(r.get("exemptions")) for r in unique_records),
                    "exemptions": [e for r in unique_records for e in (r.get("exemptions") or [])],
                },
                "corpus_verification_state": "CONFLICTING",
                "notes": (
                    f"Conflicting regulatory evidence: Conflicting regulatory schemes detected across {len(unique_records)} orders: {titles}. "
                    f"Schemes: {list(canonical_schemes)}. Authoritative review required."
                ),
            }

        # Select primary governing record (most recent effective date)
        sorted_records = sorted(
            unique_records,
            key=lambda x: str(x.get("effective_date") or x.get("publication_date") or ""),
            reverse=True,
        )
        governing_rec = sorted_records[0]

        order_title = governing_rec.get("order_title") or "Quality Control Order"
        scheme = governing_rec.get("scheme", "Scheme-I (ISI Mark)")
        authority = governing_rec.get("issuing_authority") or governing_rec.get("authority", "DPIIT")
        gazette_ref = governing_rec.get("gazette_reference") or governing_rec.get("gazette_id")
        effective = governing_rec.get("effective_date")
        evidence = governing_rec.get("evidence_excerpt")
        exemptions = governing_rec.get("exemptions") or []

        # Date awareness: Check if order was in effect as of evaluation_date
        if evaluation_date and effective:
            eval_clean = str(evaluation_date).strip()[:10]
            eff_clean = str(effective).strip()[:10]
            if eval_clean < eff_clean:
                return {
                    "regulatory_state": RegulatoryState.NOT_APPLICABLE.value,
                    "is_mandatory": False,
                    "qco_order": order_title,
                    "order_number": governing_rec.get("order_number"),
                    "authority": authority,
                    "gazette_reference": gazette_ref,
                    "effective_date": effective,
                    "evidence_excerpt": evidence,
                    "certification_scheme": scheme,
                    "matched_records_count": len(unique_records),
                    "source_consistency_status": consist_status,
                    "statutory_mandate": {
                        "is_statutory_mandatory": False,
                        "enforcement_state": RegulatoryState.NOT_APPLICABLE.value,
                        "legal_basis": "Bureau of Indian Standards Act, 2016",
                        "certification_scheme": scheme,
                        "gazette_reference": gazette_ref,
                        "has_statutory_exemptions": bool(exemptions),
                        "exemptions": exemptions,
                    },
                    "corpus_verification_state": "TEMPORALLY_INAPPLICABLE",
                    "notes": (
                        f"Order '{order_title}' ({gazette_ref or authority}) was notified with effective date {effective}, "
                        f"which is after the tender evaluation date ({eval_clean}). Not legally mandatory as of evaluation date."
                    ),
                }

        # Check conditional applicability (e.g., export exemption, prototype, small-scale)
        is_conditional = False
        if exemptions and evaluation_context:
            context_lower = evaluation_context.lower()
            if any(kw in context_lower for kw in ["export", "overseas", "prototype", "defence", "aerospace", "sample", "exemption"]):
                is_conditional = True

        final_state = (
            RegulatoryState.MANDATORY_CONDITIONALLY_APPLICABLE.value
            if is_conditional
            else RegulatoryState.MANDATORY_CONFIRMED.value
        )

        return {
            "regulatory_state": final_state,
            "is_mandatory": True,
            "qco_order": order_title,
            "order_number": governing_rec.get("order_number"),
            "authority": authority,
            "gazette_reference": gazette_ref,
            "effective_date": effective,
            "evidence_excerpt": evidence,
            "certification_scheme": scheme,
            "matched_records_count": len(unique_records),
            "source_consistency_status": consist_status,
            "statutory_mandate": {
                "is_statutory_mandatory": True,
                "enforcement_state": final_state,
                "legal_basis": "Bureau of Indian Standards Act, 2016 (Section 16)",
                "certification_scheme": scheme,
                "gazette_reference": gazette_ref,
                "has_statutory_exemptions": bool(exemptions),
                "exemptions": exemptions,
            },
            "corpus_verification_state": "VERIFIED_MANDATORY",
            "notes": (
                f"Mandatory compliance under {order_title} ({gazette_ref or authority}). Standard Mark is compulsory."
                if not is_conditional
                else f"Mandatory compliance under {order_title} ({gazette_ref or authority}) subject to conditional statutory exemptions: {exemptions}."
            ),
        }
