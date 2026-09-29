"""
Standards Knowledge Graph Builder — StandSpec AI (Layer 1 -> Knowledge Graph)
Compiles a typed, evidence-grounded standards knowledge graph from cached BIS preview HTML
or parsed standards JSONL files, conforming to RELATIONSHIP_TAXONOMY.md and DATA_PROVENANCE_CONTRACT.md.

Usage:
    python scripts/build_knowledge_graph.py --html-dir data/raw/preview_html --output data/processed/standards_graph.json
    python scripts/build_knowledge_graph.py --jsonl data/processed/CED/CED_standards.jsonl data/processed/ETD/ETD_standards.jsonl --output data/processed/standards_graph.json
    python scripts/build_knowledge_graph.py --html-dir data/raw/preview_html --top-hubs 15
"""

import sys
import json
import hashlib
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter, defaultdict
from jsonschema import Draft202012Validator

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import __version__, PARSER_VERSION, SCHEMA_VERSION
from src.parser import parse_preview_html, CANONICAL_RELATIONSHIP_TYPES
from src.preview_id import parse_standard_identity
from src.fetcher import PreviewFetcher
from src.recommendation.role_classifier import RoleClassifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("graph_builder")

# Obligation default mapping per RELATIONSHIP_TAXONOMY.md
# IMPORTANT ARCHITECTURAL SEMANTICS:
# `relationship_obligation` represents standard-to-standard normative clause dependency
# (i.e. whether adopting/implementing standard A normatively requires standard B),
# NOT statutory QCO legal mandate. Statutory mandatory enforcement (QCO, CRS, Hallmarking)
# belongs exclusively to Layer 2 (Regulatory / Mandate layer), not the technical reference graph.
OBLIGATION_MAP = {
    "normative_reference": "MANDATORY",
    "test_method": "MANDATORY",
    "safety_reference": "MANDATORY",
    "installation_reference": "CONDITIONAL",
    "material_reference": "MANDATORY",
    "measurement_method": "MANDATORY",
    "calculation_method": "MANDATORY",
    "dual_numbering": "INFORMATIVE",
    "equivalent_to": "INFORMATIVE",
    "used_in_conjunction_with": "CONDITIONAL",
    "based_on": "INFORMATIVE",
    "supersedes": "INFORMATIVE",
    "superseded_by": "INFORMATIVE",
    "terminology_reference": "INFORMATIVE",
    "related_to": "RELATED",
}

CONDITIONAL_KEYWORDS = [
    "if specified", "when required", "optional", "where applicable",
    "subject to agreement", "if agreed", "upon request", "where specified",
    "if requested", "conditional"
]

MANDATORY_KEYWORDS = [
    "shall", "must", "mandatory", "required", "compulsory"
]


def is_indian_standard(designation: str, family: str = None) -> bool:
    """
    Check if a designation or family represents an Indian Standard (IS / SP).
    Safely avoids 'IS' substring false positives (e.g. 'ISO' contains 'IS').
    """
    if family:
        fam = family.upper().strip()
        if fam in ("IS", "SP", "IS/IEC", "IS/ISO", "INDIAN STANDARD"):
            return True
        if fam in ("ISO", "IEC", "ASTM", "BS", "EN", "DIN", "IEEE"):
            return False
    desig = (designation or "").upper().strip()
    return desig.startswith("IS ") or desig.startswith("SP ") or desig.startswith("IS/") or desig.startswith("SP/")


def determine_primary_department(source_departments: list[str]) -> str | None:
    """
    Deterministic resolution of primary department from authoritative source departments.
    Prevents CLI-order or filesystem-order dependency.
    """
    if not source_departments:
        return None
    if len(source_departments) == 1:
        return source_departments[0]
    # Deterministic alphabetical precedence
    return sorted(source_departments)[0]


def citing_departments(node_id: str, edges: list[dict]) -> set[str]:
    """
    Derived graph property: departments citing this standard via incoming edges.
    NOT physically stored on the node to prevent semantic drift.
    """
    return {
        e.get("source_department")
        for e in edges
        if e.get("target") == node_id and e.get("source_department")
    }


def classify_candidate(
    designation: str,
    title: str | None,
    node_type: str,
    metadata_available: bool,
    status: str | None = None
) -> tuple[str, str]:
    """
    Classify candidate status and reason per Phase 2 candidate taxonomy.
    candidate_status: ELIGIBLE | SUPPORTING_ONLY | CONTEXT_ONLY | EXCLUDED
    """
    if not metadata_available:
        if node_type == "EXTERNAL_STANDARD":
            return "CONTEXT_ONLY", "EXTERNAL_REFERENCE"
        return "SUPPORTING_ONLY", "UNHYDRATED_STUB_REFERENCE"

    if status and status.upper() in ("WITHDRAWN", "SUPERSEDED_WITHDRAWN", "CANCELLED"):
        return "EXCLUDED", "WITHDRAWN"

    if node_type == "EXTERNAL_STANDARD":
        return "CONTEXT_ONLY", "EXTERNAL_REFERENCE"

    title_lower = (title or "").lower()
    is_test = any(phrase in title_lower for phrase in [
        "methods of test", "method of test", "code of practice for testing",
        "testing of", "determination of", "test method", "methods for test"
    ]) or designation.startswith("IS 10810")
    if is_test:
        return "SUPPORTING_ONLY", "TEST_METHOD"

    is_glossary = any(phrase in title_lower for phrase in [
        "glossary of terms", "terminology", "vocabulary", "glossary"
    ]) or designation.startswith("IS 1885")
    if is_glossary:
        return "SUPPORTING_ONLY", "TERMINOLOGY_REFERENCE"

    if designation.startswith("IS/IEC") or designation.startswith("IS/ISO"):
        return "ELIGIBLE", "BIS_ADOPTED_INTERNATIONAL"

    return "ELIGIBLE", "PRIMARY_BIS_STANDARD"


def compute_node_evidence_and_readiness(
    node: dict,
    metadata_available: bool,
    identity_verified: bool,
    document_available: bool,
    has_scope: bool,
    has_refs: bool,
    has_lifecycle: bool,
    has_regulatory: bool = False,
) -> dict:
    """
    Compute 8 atomic evidence states and 4 derived readiness levels.
    """
    title = node.get("title")
    scope = node.get("scope")
    ics = node.get("ics_codes") or []

    meta_avail = bool(metadata_available)
    details_avail = bool(node.get("committee") or ics or node.get("technical_committees"))
    ident_ver = bool(identity_verified)
    doc_avail = bool(document_available)
    scope_avail = bool(has_scope and scope and str(scope).strip())
    ref_avail = bool(has_refs or node.get("references_status") == "parsed")
    
    # Trust Mandate P1-A & P1-B: Lifecycle evidence requires verified status/provenance, not merely an isolated year
    has_status = bool(node.get("status") and str(node.get("status")).upper() not in ("UNKNOWN", "NONE", ""))
    has_lifecycle_evidence = bool(node.get("lifecycle") and (node["lifecycle"].get("status") or node["lifecycle"].get("effective_date")))
    life_avail = bool(has_lifecycle_evidence or (has_lifecycle and has_status))
    
    reg_avail = bool(has_regulatory or node.get("qco_mandatory") is not None)

    meta_ready = meta_avail
    retrieval_ready = meta_avail and bool(title or scope_avail or ics)
    applicability_ready = ident_ver and doc_avail and scope_avail
    rec_ready = applicability_ready and life_avail

    # Role classification persistence (P1-B Step 1)
    role_info = RoleClassifier.classify_with_evidence(node)

    return {
        "metadata_available": meta_avail,
        "details_available": details_avail,
        "identity_verified": ident_ver,
        "document_available": doc_avail,
        "scope_evidence_available": scope_avail,
        "reference_evidence_available": ref_avail,
        "lifecycle_evidence_available": life_avail,
        "regulatory_evidence_available": reg_avail,
        "metadata_ready": meta_ready,
        "retrieval_ready": retrieval_ready,
        "applicability_ready": applicability_ready,
        "recommendation_ready": rec_ready,
        "standard_role": role_info["standard_role"],
        "role_confidence": role_info["role_confidence"],
        "role_reason": role_info["role_reason"],
        "role_source": role_info["role_source"],
        "role_classifier_version": "1.0.0-phase-d",
    }


def find_and_classify_reciprocal_pairs(edges: list[dict]) -> tuple[list[tuple], dict[str, int]]:
    """
    Identify directed reciprocal edge pairs (observed cycles) and classify them.
    """
    edge_map = {(e["source"], e["target"]): e for e in edges}
    pairs = []
    seen = set()
    classification = Counter()

    for (s, t), e1 in edge_map.items():
        if (t, s) in edge_map:
            key = (min(s, t), max(s, t))
            if key not in seen:
                seen.add(key)
                e2 = edge_map[(t, s)]
                pairs.append((s, t, e1["relationship"], e2["relationship"]))

                s_base = s.split("(")[0].strip()
                t_base = t.split("(")[0].strip()
                if s_base == t_base and ("Part" in s or "Part" in t):
                    classification["part_cross_reference"] += 1
                elif e1["relationship"] == "normative_reference" and e2["relationship"] == "normative_reference":
                    classification["normative_reference_reciprocal"] += 1
                elif "dual_numbering" in (e1["relationship"], e2["relationship"]) or "equivalent_to" in (e1["relationship"], e2["relationship"]):
                    classification["companion_standard"] += 1
                else:
                    classification["possible_extraction_artifact"] += 1

    return pairs, dict(classification)


def _content_hash(graph: dict) -> str:
    """
    Hash graph content excluding ALL nondeterministic, runtime environment paths, and self-referential fields.
    Guarantees cross-platform reproducibility between Windows and Linux.
    """
    EXCLUDED_FIELDS = {"built_at", "release_id", "content_hash", "source_path"}
    content = {k: v for k, v in graph.items() if k not in EXCLUDED_FIELDS}
    if "nodes" in content and isinstance(content["nodes"], list):
        content["nodes"] = sorted(content["nodes"], key=lambda n: n.get("id", ""))
    if "edges" in content and isinstance(content["edges"], list):
        content["edges"] = sorted(
            content["edges"],
            key=lambda e: (e.get("source", ""), e.get("target", ""), e.get("relationship", ""))
        )
    canonical = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def derive_obligation(relationship: str, context: dict = None) -> str:
    """
    Derive obligation semantics per RELATIONSHIP_TAXONOMY.md.
    Decoupled from relationship: context dictates obligation.
    """
    if context is None:
        return OBLIGATION_MAP.get(relationship, "UNKNOWN")

    evidence_text = (context.get("text") or context.get("evidence_text") or context.get("sentence_text") or "").lower()
    source_sec = (context.get("source_section") or "").upper()
    method = (context.get("extraction_method") or "").lower()
    title = (context.get("title") or "").lower()
    combined_text = f"{evidence_text} {title}".strip()

    # 1. Informative markers in section or text
    if any(inf in combined_text for inf in ["informative", "for information", "note:"]) or "INFORMATIVE" in source_sec:
        return "INFORMATIVE"

    # 2. Inherent informative relationship types
    if relationship in {
        "dual_numbering",
        "equivalent_to",
        "based_on",
        "supersedes",
        "superseded_by",
        "terminology_reference",
    }:
        return "INFORMATIVE"

    # 3. Conditional markers in evidence text
    if any(kw in combined_text for kw in CONDITIONAL_KEYWORDS):
        return "CONDITIONAL"

    # 4. Mandatory / Normative references
    if relationship in {
        "normative_reference",
        "test_method",
        "safety_reference",
        "material_reference",
        "measurement_method",
        "calculation_method",
    }:
        if method == "html_table_row" or source_sec == "REFERENCES":
            return "MANDATORY"
        if any(w in combined_text for w in MANDATORY_KEYWORDS):
            return "MANDATORY"
        if source_sec in ("NATIONAL FOREWORD", "FOREWORD", "NATIONAL_FOREWORD"):
            return "INFORMATIVE"
        return "MANDATORY"

    # 5. Conjunction / installation
    if relationship in {"used_in_conjunction_with", "installation_reference"}:
        if any(w in combined_text for w in MANDATORY_KEYWORDS):
            return "MANDATORY"
        return "CONDITIONAL"

    # 6. Fallback related_to
    if relationship == "related_to":
        if any(w in combined_text for w in MANDATORY_KEYWORDS):
            return "MANDATORY"
        if any(w in combined_text for w in ["optional", "if"]):
            return "CONDITIONAL"
        return "RELATED"

    return OBLIGATION_MAP.get(relationship, "UNKNOWN")


def build_graph_from_html(html_dir: Path) -> dict:
    """Scan all HTML preview files and build node/edge graph representation."""
    html_files = sorted(html_dir.glob("*.html"))
    logger.info(f"Found {len(html_files)} HTML files in {html_dir}")

    nodes = {}
    edges = []
    seen_edge_keys = set()
    fetcher = PreviewFetcher(cache_dir=html_dir)

    for filepath in html_files:
        try:
            html = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Failed to read {filepath}: {e}")
            continue

        source_id = filepath.stem
        parsed = parse_preview_html(html, source_standard=source_id)

        header_text = parsed.get("header_text") or ""
        page_ident = fetcher.extract_page_identity(html)
        if page_ident and page_ident.get("normalized_designation"):
            canonical_source = page_ident["normalized_designation"]
        else:
            canonical_source = f"IS {source_id.replace('_', ' ')}"

        ident_status, _, _ = fetcher.verify_page_identity(None, html)
        page_self_identified = (ident_status == "match_version_verified")
        source_identity_verified = False  # In raw HTML build without manifest
        edge_ver_status = "SELF_IDENTIFIED_ONLY" if page_self_identified else "UNRESOLVED"
        source_id_state = "SELF_IDENTIFIED" if page_self_identified else "UNRESOLVED"

        is_is = is_indian_standard(canonical_source, parsed.get("family"))
        node_type = "INDIAN_STANDARD" if is_is else "EXTERNAL_STANDARD"

        cand_status, cand_reason = classify_candidate(
            canonical_source, parsed.get("title"), node_type, metadata_available=True
        )

        node_data = {
            "id": canonical_source,
            "node_type": node_type,
            "designation": canonical_source,
            "title": parsed.get("title"),
            "header_text": header_text,
            "committee": parsed.get("committee"),
            "technical_committees": [parsed.get("committee")] if parsed.get("committee") else [],
            "primary_department": None,
            "source_departments": [],
            "family": parsed.get("family") or ("IS" if is_is else None),
            "base_number": parsed.get("base_number"),
            "part": parsed.get("part"),
            "section": parsed.get("section"),
            "year": parsed.get("year"),
            "ics_raw": parsed.get("ics_raw"),
            "ics_codes": parsed.get("ics_codes", []),
            "scope": (parsed.get("scope") or {}).get("text"),
            "scope_status": (parsed.get("scope") or {}).get("status"),
            "references_status": parsed.get("references_status", "parsed" if parsed.get("formal_references") else "none_found"),
            "has_cached_preview": True,
            "is_hydrated": True,
            "is_recommendation_eligible": (cand_status == "ELIGIBLE"),
            "preview_id": source_id,
            "candidate_status": cand_status,
            "candidate_reason": cand_reason,
        }
        node_data.update(compute_node_evidence_and_readiness(
            node_data,
            metadata_available=True,
            identity_verified=page_self_identified,
            document_available=True,
            has_scope=bool((parsed.get("scope") or {}).get("text")),
            has_refs=bool(parsed.get("formal_references")),
            has_lifecycle=bool(parsed.get("year")),
        ))

        nodes[canonical_source] = node_data

        # Process formal references
        for ref in parsed.get("formal_references", []):
            target = ref.get("target", {})
            target_desig = target.get("designation")
            if not target_desig:
                continue

            if target_desig not in nodes:
                is_target_is = is_indian_standard(target_desig, target.get("family"))
                target_node_type = "INDIAN_STANDARD" if is_target_is else "EXTERNAL_STANDARD"
                t_cand_status, t_cand_reason = classify_candidate(
                    target_desig, ref.get("title"), target_node_type, metadata_available=False
                )
                stub_data = {
                    "id": target_desig,
                    "node_type": target_node_type,
                    "designation": target_desig,
                    "title": ref.get("title"),
                    "header_text": None,
                    "committee": None,
                    "technical_committees": [],
                    "primary_department": None,
                    "source_departments": [],
                    "family": target.get("family"),
                    "base_number": target.get("base_number"),
                    "part": target.get("part"),
                    "section": target.get("section"),
                    "year": target.get("year"),
                    "ics_raw": None,
                    "ics_codes": [],
                    "scope": None,
                    "scope_status": None,
                    "references_status": "absent",
                    "has_cached_preview": False,
                    "is_hydrated": False,
                    "is_recommendation_eligible": False,
                    "preview_id": None,
                    "candidate_status": t_cand_status,
                    "candidate_reason": t_cand_reason,
                }
                stub_data.update(compute_node_evidence_and_readiness(
                    stub_data,
                    metadata_available=False,
                    identity_verified=False,
                    document_available=False,
                    has_scope=False,
                    has_refs=False,
                    has_lifecycle=bool(target.get("year")),
                ))
                nodes[target_desig] = stub_data

            rel = ref.get("relationship", "normative_reference")
            if rel not in CANONICAL_RELATIONSHIP_TYPES:
                rel = "normative_reference"

            evidence = ref.get("evidence", {})
            obligation_ctx = {
                "text": evidence.get("text"),
                "source_section": evidence.get("source_section", "REFERENCES"),
                "extraction_method": evidence.get("extraction_method", "html_table_row"),
                "title": ref.get("title"),
            }
            obligation = derive_obligation(rel, obligation_ctx)
            is_structural = (ref.get("relationship_confidence") == "structural")
            confidence = 0.9 if (is_structural and page_self_identified) else 0.8
            rel_obs = "EXPLICIT_FROM_SOURCE" if is_structural else "INFERRED"
            rel_conf = "MEDIUM" if page_self_identified else "LOW"

            edge_key = (canonical_source, target_desig, rel)
            if edge_key not in seen_edge_keys:
                seen_edge_keys.add(edge_key)
                edges.append({
                    "source": canonical_source,
                    "target": target_desig,
                    "source_department": None,
                    "relationship": rel,
                    "relationship_obligation": obligation,
                    "edge_origin": "DIRECT",
                    "edge_type": "DIRECT",
                    "source_identity_state": source_id_state,
                    "relationship_observation": rel_obs,
                    "relationship_confidence_state": rel_conf,
                    "confidence": confidence,
                    "source_tier": 1,
                    "verified": False,
                    "edge_verification_status": edge_ver_status,
                    "manifest_identity_verified": False,
                    "page_self_identified": page_self_identified,
                    "source_extracted": True,
                    "source_page_identity_verified": source_identity_verified,
                    "relationship_verified": is_structural,
                    "evidence_span": ref.get("title") or f"Table row reference in {canonical_source}",
                    "extraction_details": {
                        "source_section": evidence.get("source_section", "REFERENCES"),
                        "extraction_method": evidence.get("extraction_method", "html_table_row"),
                        "continuation_resolved": evidence.get("continuation_resolved", False),
                        "table_index": evidence.get("table_index"),
                        "row_index": evidence.get("row_index"),
                        "column_name": evidence.get("column_name"),
                        "sentence_text": evidence.get("sentence_text"),
                        "dual_numbering_raw": ref.get("dual_numbering_raw"),
                        "linked_standard": ref.get("linked_standard"),
                    }
                })

        # Process prose references
        for ref in parsed.get("prose_references", []):
            target = ref.get("target", {})
            target_desig = target.get("designation")
            if not target_desig:
                continue

            if target_desig not in nodes:
                is_target_is = ("IS" in target.get("family", "") or target_desig.startswith("IS "))
                target_node_type = "INDIAN_STANDARD" if is_target_is else "EXTERNAL_STANDARD"
                t_cand_status, t_cand_reason = classify_candidate(
                    target_desig, None, target_node_type, metadata_available=False
                )
                stub_data = {
                    "id": target_desig,
                    "node_type": target_node_type,
                    "designation": target_desig,
                    "title": None,
                    "header_text": None,
                    "committee": None,
                    "technical_committees": [],
                    "primary_department": None,
                    "source_departments": [],
                    "family": target.get("family"),
                    "base_number": target.get("base_number"),
                    "part": target.get("part"),
                    "section": target.get("section"),
                    "year": target.get("year"),
                    "ics_raw": None,
                    "ics_codes": [],
                    "scope": None,
                    "scope_status": None,
                    "references_status": "absent",
                    "has_cached_preview": False,
                    "is_hydrated": False,
                    "is_recommendation_eligible": False,
                    "preview_id": None,
                    "candidate_status": t_cand_status,
                    "candidate_reason": t_cand_reason,
                }
                stub_data.update(compute_node_evidence_and_readiness(
                    stub_data,
                    metadata_available=False,
                    identity_verified=False,
                    document_available=False,
                    has_scope=False,
                    has_refs=False,
                    has_lifecycle=bool(target.get("year")),
                ))
                nodes[target_desig] = stub_data

            rel = ref.get("relationship", "related_to")
            if rel not in CANONICAL_RELATIONSHIP_TYPES:
                rel = "related_to"

            evidence = ref.get("evidence", {})
            obligation_ctx = {
                "text": ref.get("evidence_sentence") or evidence.get("text"),
                "source_section": "NATIONAL FOREWORD",
                "extraction_method": "prose_phrase_scan",
                "title": None,
            }
            obligation = derive_obligation(rel, obligation_ctx)
            is_explicit_prose = (rel != "related_to")
            confidence = 0.85 if is_explicit_prose else 0.5
            rel_obs = "CORROBORATED" if is_explicit_prose else "INFERRED"
            rel_conf = "MEDIUM" if page_self_identified else "LOW"

            edge_key = (canonical_source, target_desig, rel)
            if edge_key not in seen_edge_keys:
                seen_edge_keys.add(edge_key)
                edges.append({
                    "source": canonical_source,
                    "target": target_desig,
                    "source_department": None,
                    "relationship": rel,
                    "relationship_obligation": obligation,
                    "edge_origin": "DIRECT",
                    "edge_type": "DIRECT",
                    "source_identity_state": source_id_state,
                    "relationship_observation": rel_obs,
                    "relationship_confidence_state": rel_conf,
                    "confidence": confidence,
                    "source_tier": 1,
                    "verified": False,
                    "edge_verification_status": edge_ver_status,
                    "manifest_identity_verified": False,
                    "page_self_identified": page_self_identified,
                    "source_extracted": True,
                    "source_page_identity_verified": source_identity_verified,
                    "relationship_verified": is_explicit_prose,
                    "evidence_span": ref.get("evidence_sentence"),
                    "extraction_details": {
                        "source_section": "NATIONAL_FOREWORD",
                        "extraction_method": "prose_phrase_scan",
                        "continuation_resolved": False,
                        "table_index": None,
                        "row_index": None,
                        "column_name": None,
                        "sentence_text": ref.get("evidence_sentence"),
                        "dual_numbering_raw": None,
                        "linked_standard": None,
                    }
                })

    hydrated_count = sum(1 for n in nodes.values() if n.get("is_hydrated", False))
    unhydrated_count = len(nodes) - hydrated_count
    rec_eligible_count = sum(1 for n in nodes.values() if n.get("is_recommendation_eligible", False))
    direct_edges_count = sum(1 for e in edges if e.get("edge_origin") == "DIRECT")
    inferred_edges_count = sum(1 for e in edges if e.get("edge_origin") == "INFERRED")

    reciprocal_pairs, reciprocal_classification = find_and_classify_reciprocal_pairs(edges)

    graph = {
        "graph_version": "1.2.1",
        "schema_version": "1.2.0",
        "parser_version": "1.2.1",
        "release_id": "STANDSPEC_KG_2026_09",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "html_dir",
        "source_path": str(html_dir),
        "description": "StandSpec AI Standards Knowledge Graph — Typed, evidence-grounded relational standards network.",
        "nodes_count": len(nodes),
        "hydrated_nodes_count": hydrated_count,
        "unhydrated_nodes_count": unhydrated_count,
        "recommendation_eligible_count": rec_eligible_count,
        "edges_count": len(edges),
        "direct_edges_count": direct_edges_count,
        "inferred_edges_count": inferred_edges_count,
        "reciprocal_pairs_count": len(reciprocal_pairs),
        "reciprocal_pairs": [list(p) for p in reciprocal_pairs],
        "reciprocal_classification": reciprocal_classification,
        "source_departments": [],
        "department_node_counts": {},
        "department_hydrated_counts": {},
        "nodes": list(nodes.values()),
        "edges": edges,
    }
    graph["content_hash"] = _content_hash(graph)
    return graph


def _get_v12_identity_verified(record: dict) -> bool:
    """Determine whether a V1.2 record's source identity was verified."""
    src = record.get("source", {})
    identity_match = src.get("identity_match", "unknown")
    content = record.get("content", {})
    evidence_verified = content.get("evidence_verified", False)

    if identity_match in ("match_version_verified", "match"):
        return True
    if identity_match in ("match_version_uncertain", "match_identity_only_version_uncertain", "mismatch"):
        return False

    prov = record.get("provenance", {})
    extraction_val = prov.get("extraction_validation", {})
    return extraction_val.get("identity_verified", False) or evidence_verified


def build_graph_from_jsonl(jsonl_paths) -> dict:
    """
    Build graph representation from one or more V1.2 canonical standards.jsonl files.
    Accepts a single Path or a list of Paths for multi-department unified graph.
    """
    if isinstance(jsonl_paths, (str, Path)):
        jsonl_paths = [Path(jsonl_paths)]
    else:
        jsonl_paths = [Path(p) for p in jsonl_paths]

    logger.info(f"Building knowledge graph from {len(jsonl_paths)} JSONL file(s): {[str(p) for p in jsonl_paths]}")
    nodes = {}
    edges = []
    seen_edge_keys = set()

    for jsonl_path in jsonl_paths:
        logger.info(f"Processing JSONL: {jsonl_path}")
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                identity = record.get("identity", {})
                canonical_source = identity.get("standard_designation") or record.get("standard_number") or record.get("normalized_designation")
                if not canonical_source:
                    continue

                source_identity_verified = _get_v12_identity_verified(record)
                content = record.get("content", {})
                src = record.get("source", {})

                def _field(key):
                    return content.get(key, record.get(key))

                is_is = is_indian_standard(canonical_source, identity.get("family"))
                node_type = "INDIAN_STANDARD" if is_is else "EXTERNAL_STANDARD"
                dept = record.get("department")
                committee = _field("committee")
                title = _field("title")
                scope_text = (_field("scope") or {}).get("text") if isinstance(_field("scope"), dict) else _field("scope")
                ics_raw = _field("ics_raw")
                ics_codes = _field("ics_codes") if _field("ics_codes") is not None else record.get("ics_codes", [])
                has_cached_preview = bool(src.get("matched_preview_id") or record.get("preview_id"))
                preview_id = src.get("matched_preview_id") or record.get("preview_id")
                rec_status = (
                    _field("status")
                    or record.get("status")
                    or (record.get("lifecycle") or {}).get("status")
                    or record.get("standards_status")
                )

                cand_status, cand_reason = classify_candidate(
                    canonical_source, title, node_type, metadata_available=True, status=rec_status
                )

                existing = nodes.get(canonical_source)
                if existing:
                    if existing.get("is_hydrated"):
                        # Already hydrated from another file/department: merge departments deterministically
                        existing_depts = existing.get("source_departments", [])
                        if dept and dept not in existing_depts:
                            existing_depts.append(dept)
                        existing["source_departments"] = sorted(existing_depts)
                        existing["primary_department"] = determine_primary_department(existing["source_departments"])
                        if committee:
                            existing.setdefault("technical_committees", [])
                            if committee not in existing["technical_committees"]:
                                existing["technical_committees"].append(committee)
                    else:
                        # Existing was an unhydrated stub: upgrade to fully hydrated catalogue record!
                        source_depts = [dept] if dept else []
                        existing.update({
                            "node_type": node_type,
                            "designation": canonical_source,
                            "title": title or existing.get("title"),
                            "header_text": _field("header_text"),
                            "committee": committee,
                            "technical_committees": [committee] if committee else [],
                            "primary_department": determine_primary_department(source_depts),
                            "source_departments": sorted(source_depts),
                            "ics_raw": ics_raw,
                            "ics_codes": ics_codes,
                            "scope": scope_text,
                            "scope_status": (_field("scope") or {}).get("status") if isinstance(_field("scope"), dict) else None,
                            "references_status": content.get("references_status", "absent"),
                            "has_cached_preview": has_cached_preview,
                            "is_hydrated": True,
                            "is_recommendation_eligible": (cand_status == "ELIGIBLE"),
                            "preview_id": preview_id,
                            "candidate_status": cand_status,
                            "candidate_reason": cand_reason,
                        })
                        existing.update(compute_node_evidence_and_readiness(
                            existing,
                            metadata_available=True,
                            identity_verified=source_identity_verified,
                            document_available=has_cached_preview,
                            has_scope=bool(scope_text),
                            has_refs=bool(content.get("references_status") == "parsed" or record.get("references")),
                            has_lifecycle=bool(identity.get("year") or record.get("year")),
                        ))
                else:
                    # New hydrated catalogue node
                    source_depts = [dept] if dept else []
                    new_node = {
                        "id": canonical_source,
                        "node_type": node_type,
                        "designation": canonical_source,
                        "title": title,
                        "header_text": _field("header_text"),
                        "committee": committee,
                        "technical_committees": [committee] if committee else [],
                        "primary_department": determine_primary_department(source_depts),
                        "source_departments": sorted(source_depts),
                        "family": identity.get("family") or ("IS" if is_is else None),
                        "base_number": identity.get("base_number"),
                        "part": identity.get("part"),
                        "section": identity.get("section"),
                        "year": identity.get("year") or record.get("year"),
                        "ics_raw": ics_raw,
                        "ics_codes": ics_codes,
                        "scope": scope_text,
                        "scope_status": (_field("scope") or {}).get("status") if isinstance(_field("scope"), dict) else None,
                        "references_status": content.get("references_status", "absent"),
                        "has_cached_preview": has_cached_preview,
                        "is_hydrated": True,
                        "is_recommendation_eligible": (cand_status == "ELIGIBLE"),
                        "preview_id": preview_id,
                        "candidate_status": cand_status,
                        "candidate_reason": cand_reason,
                    }
                    new_node.update(compute_node_evidence_and_readiness(
                        new_node,
                        metadata_available=True,
                        identity_verified=source_identity_verified,
                        document_available=has_cached_preview,
                        has_scope=bool(scope_text),
                        has_refs=bool(content.get("references_status") == "parsed" or record.get("references")),
                        has_lifecycle=bool(identity.get("year") or record.get("year")),
                    ))
                    nodes[canonical_source] = new_node

                # Process all references for this record (NEVER skipped via continue)
                all_refs = list(record.get("references", []))
                if not all_refs:
                    for ref_list_key in ("formal_references", "prose_references"):
                        all_refs.extend(record.get(ref_list_key, []))

                for ref in all_refs:
                    target = ref.get("target", {})
                    target_desig = target.get("designation")
                    if not target_desig:
                        continue

                    if target_desig not in nodes:
                        is_target_is = is_indian_standard(target_desig, target.get("family"))
                        target_node_type = "INDIAN_STANDARD" if is_target_is else "EXTERNAL_STANDARD"
                        t_cand_status, t_cand_reason = classify_candidate(
                            target_desig, ref.get("title"), target_node_type, metadata_available=False
                        )
                        # Stub nodes have NO source_departments (provenance lives on the citing edge)
                        stub_node = {
                            "id": target_desig,
                            "node_type": target_node_type,
                            "designation": target_desig,
                            "title": ref.get("title"),
                            "header_text": None,
                            "committee": None,
                            "technical_committees": [],
                            "primary_department": None,
                            "source_departments": [],
                            "family": target.get("family"),
                            "base_number": target.get("base_number"),
                            "part": target.get("part"),
                            "section": target.get("section"),
                            "year": target.get("year"),
                            "ics_raw": None,
                            "ics_codes": [],
                            "scope": None,
                            "scope_status": None,
                            "references_status": "absent",
                            "has_cached_preview": False,
                            "is_hydrated": False,
                            "is_recommendation_eligible": False,
                            "preview_id": None,
                            "candidate_status": t_cand_status,
                            "candidate_reason": t_cand_reason,
                        }
                        stub_node.update(compute_node_evidence_and_readiness(
                            stub_node,
                            metadata_available=False,
                            identity_verified=False,
                            document_available=False,
                            has_scope=False,
                            has_refs=False,
                            has_lifecycle=bool(target.get("year")),
                        ))
                        nodes[target_desig] = stub_node

                    rel = ref.get("relationship", "normative_reference")
                    if rel not in CANONICAL_RELATIONSHIP_TYPES:
                        rel = "normative_reference"

                    evidence = ref.get("evidence", {})
                    obligation_ctx = {
                        "text": evidence.get("text") or ref.get("evidence_sentence"),
                        "source_section": evidence.get("source_section", "REFERENCES"),
                        "extraction_method": evidence.get("extraction_method", "html_table_row"),
                        "title": ref.get("title"),
                    }
                    obligation = derive_obligation(rel, obligation_ctx)

                    is_structural = (ref.get("relationship_confidence") == "structural")

                    # Granular edge verification
                    identity_match = src.get("identity_match", "unknown")
                    has_page_ident = bool((src.get("page_identity_evidence") or {}).get("normalized_designation"))
                    if source_identity_verified:
                        source_id_state = "VERIFIED"
                    elif identity_match in ("match_version_uncertain", "match_identity_only_version_uncertain", "mismatch", "unresolved"):
                        source_id_state = "UNRESOLVED"
                    elif has_page_ident:
                        source_id_state = "SELF_IDENTIFIED"
                    else:
                        source_id_state = "UNRESOLVED"

                    rel_obs = "EXPLICIT_FROM_SOURCE" if is_structural else "INFERRED"

                    if source_id_state == "VERIFIED" and rel_obs == "EXPLICIT_FROM_SOURCE":
                        rel_conf_state = "HIGH"
                        confidence = 1.0
                    elif source_id_state == "VERIFIED" and rel_obs == "INFERRED":
                        rel_conf_state = "MEDIUM"
                        confidence = 0.8
                    elif source_id_state == "SELF_IDENTIFIED" and rel_obs == "EXPLICIT_FROM_SOURCE":
                        rel_conf_state = "MEDIUM"
                        confidence = 0.8
                    else:
                        rel_conf_state = "LOW"
                        confidence = 0.6

                    page_self_ident = bool(source_id_state in ("VERIFIED", "SELF_IDENTIFIED"))
                    is_verified_edge = (source_id_state == "VERIFIED" and rel_obs == "EXPLICIT_FROM_SOURCE")
                    edge_ver_status = "VERIFIED" if is_verified_edge else ("SELF_IDENTIFIED_ONLY" if source_id_state == "SELF_IDENTIFIED" else "UNRESOLVED")

                    edge_key = (canonical_source, target_desig, rel)
                    if edge_key not in seen_edge_keys:
                        seen_edge_keys.add(edge_key)
                        edges.append({
                            "source": canonical_source,
                            "target": target_desig,
                            "source_department": dept,
                            "relationship": rel,
                            "relationship_obligation": obligation,
                            "edge_origin": "DIRECT",
                            "edge_type": "DIRECT",
                            "source_identity_state": source_id_state,
                            "relationship_observation": rel_obs,
                            "relationship_confidence_state": rel_conf_state,
                            "confidence": confidence,
                            "source_tier": 1,
                            "verified": is_verified_edge,
                            "edge_verification_status": edge_ver_status,
                            "manifest_identity_verified": source_identity_verified,
                            "page_self_identified": page_self_ident,
                            "source_extracted": True,
                            "source_page_identity_verified": source_identity_verified,
                            "relationship_verified": is_structural,
                            "evidence_span": ref.get("title") or ref.get("evidence_sentence") or f"Reference in {canonical_source}",
                            "extraction_details": {
                                "source_section": evidence.get("source_section", "REFERENCES"),
                                "extraction_method": evidence.get("extraction_method", "html_table_row"),
                                "continuation_resolved": evidence.get("continuation_resolved", False),
                                "table_index": evidence.get("table_index"),
                                "row_index": evidence.get("row_index"),
                                "column_name": evidence.get("column_name"),
                                "sentence_text": evidence.get("sentence_text"),
                                "dual_numbering_raw": ref.get("dual_numbering_raw"),
                                "linked_standard": ref.get("linked_standard"),
                            }
                        })

    hydrated_count = sum(1 for n in nodes.values() if n.get("is_hydrated", False))
    unhydrated_count = len(nodes) - hydrated_count
    rec_eligible_count = sum(1 for n in nodes.values() if n.get("is_recommendation_eligible", False))
    direct_edges_count = sum(1 for e in edges if e.get("edge_origin") == "DIRECT")
    inferred_edges_count = sum(1 for e in edges if e.get("edge_origin") == "INFERRED")

    reciprocal_pairs, reciprocal_classification = find_and_classify_reciprocal_pairs(edges)

    # Department coverage from authoritative primary records
    source_departments = set()
    dept_node_counts = Counter()
    dept_hydrated_counts = Counter()
    for n in nodes.values():
        for d in n.get("source_departments", []):
            source_departments.add(d)
            dept_node_counts[d] += 1
            if n.get("is_hydrated"):
                dept_hydrated_counts[d] += 1

    graph = {
        "graph_version": "1.2.1",
        "schema_version": "1.2.0",
        "parser_version": "1.2.1",
        "release_id": "STANDSPEC_KG_2026_09",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "jsonl",
        "source_path": ", ".join(str(p).replace("\\", "/") for p in jsonl_paths),
        "description": "StandSpec AI Standards Knowledge Graph — Typed, evidence-grounded relational standards network.",
        "nodes_count": len(nodes),
        "hydrated_nodes_count": hydrated_count,
        "unhydrated_nodes_count": unhydrated_count,
        "recommendation_eligible_count": rec_eligible_count,
        "primary_candidate_count": sum(1 for n in nodes.values() if n.get("candidate_status") == "ELIGIBLE"),
        "supporting_candidate_count": sum(1 for n in nodes.values() if n.get("candidate_status") == "SUPPORTING_ONLY"),
        "context_count": sum(1 for n in nodes.values() if n.get("candidate_status") == "CONTEXT_ONLY"),
        "applicability_ready_count": sum(1 for n in nodes.values() if n.get("applicability_ready", False)),
        "recommendation_ready_count": sum(1 for n in nodes.values() if n.get("recommendation_ready", False)),
        "edges_count": len(edges),
        "direct_edges_count": direct_edges_count,
        "inferred_edges_count": inferred_edges_count,
        "reciprocal_pairs_count": len(reciprocal_pairs),
        "reciprocal_pairs": [list(p) for p in reciprocal_pairs],
        "reciprocal_classification": reciprocal_classification,
        "source_departments": sorted(source_departments),
        "department_node_counts": dict(dept_node_counts),
        "department_hydrated_counts": dict(dept_hydrated_counts),
        "nodes": list(nodes.values()),
        "edges": edges,
    }
    graph["content_hash"] = _content_hash(graph)
    return graph


def validate_graph(graph: dict, schema_path: Path = None) -> tuple[bool, list[str]]:
    """
    Validate a graph dict against schemas/standards_graph.schema.json.
    Returns (is_valid, list_of_error_messages).
    """
    if schema_path is None:
        schema_path = PROJECT_ROOT / "schemas" / "standards_graph.schema.json"
    if not schema_path.exists():
        return True, []

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        Draft202012Validator.check_schema(schema)
    except Exception as e:
        return True, [f"schema_unavailable: {e}"]

    validator = Draft202012Validator(schema)
    errors = []
    for err in validator.iter_errors(graph):
        path = "/".join(str(p) for p in err.path) or "(root)"
        errors.append(f"Graph schema violation at '{path}': {err.message}")

    return len(errors) == 0, errors


def compute_graph_statistics(graph: dict) -> dict:
    """Compute structural graph properties and centralities."""
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]

    in_degree = Counter()
    out_degree = Counter()
    rel_counts = Counter()
    ob_counts = Counter()
    node_types = Counter()
    candidate_statuses = Counter()
    readiness_counts = Counter()

    adj = defaultdict(set)

    for n in graph["nodes"]:
        node_types[n.get("node_type", "UNKNOWN")] += 1
        candidate_statuses[n.get("candidate_status", "UNKNOWN")] += 1
        if n.get("metadata_ready"):
            readiness_counts["metadata_ready"] += 1
        if n.get("retrieval_ready"):
            readiness_counts["retrieval_ready"] += 1
        if n.get("applicability_ready"):
            readiness_counts["applicability_ready"] += 1
        if n.get("recommendation_ready"):
            readiness_counts["recommendation_ready"] += 1

    for e in edges:
        s = e["source"]
        t = e["target"]
        r = e["relationship"]
        ob = e["relationship_obligation"]

        out_degree[s] += 1
        in_degree[t] += 1
        rel_counts[r] += 1
        ob_counts[ob] += 1

        adj[s].add(t)
        adj[t].add(s)

    # Connected components using BFS
    visited = set()
    components = []
    for node_id in nodes:
        if node_id not in visited:
            comp = []
            queue = [node_id]
            visited.add(node_id)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            components.append(comp)

    components.sort(key=len, reverse=True)

    hydrated_nodes = sum(1 for n in nodes.values() if n.get("is_hydrated", False))
    unhydrated_nodes = len(nodes) - hydrated_nodes
    rec_eligible = sum(1 for n in nodes.values() if n.get("is_recommendation_eligible", False))

    return {
        "total_nodes": len(nodes),
        "hydrated_nodes": hydrated_nodes,
        "unhydrated_nodes": unhydrated_nodes,
        "recommendation_eligible_nodes": rec_eligible,
        "node_types": dict(node_types),
        "candidate_statuses": dict(candidate_statuses),
        "readiness_tiers": dict(readiness_counts),
        "total_edges": len(edges),
        "direct_edges": sum(1 for e in edges if e.get("edge_origin") == "DIRECT"),
        "inferred_edges": sum(1 for e in edges if e.get("edge_origin") == "INFERRED"),
        "reciprocal_pairs_count": graph.get("reciprocal_pairs_count", 0),
        "reciprocal_classification": graph.get("reciprocal_classification", {}),
        "relationship_distribution": dict(rel_counts),
        "obligation_distribution": dict(ob_counts),
        "top_in_degree_hubs": in_degree.most_common(15),
        "top_out_degree_standards": out_degree.most_common(10),
        "connected_components_count": len(components),
        "largest_component_size": len(components[0]) if components else 0,
        "content_hash": graph.get("content_hash"),
    }


def print_graph_report(stats: dict):
    print("=" * 70)
    print("StandSpec AI — Standards Knowledge Graph Report (v1.2.1)")
    print("=" * 70)
    print(f"Total Nodes: {stats['total_nodes']} ({stats['node_types']})")
    print(f"  - Hydrated Nodes: {stats['hydrated_nodes']}")
    print(f"  - Unhydrated (Stub) Nodes: {stats['unhydrated_nodes']}")
    print(f"  - Recommendation Eligible: {stats['recommendation_eligible_nodes']}")
    print(f"Candidate Taxonomy: {stats.get('candidate_statuses')}")
    print(f"Readiness Tiers: {stats.get('readiness_tiers')}")
    print(f"Total Edges: {stats['total_edges']} (Direct: {stats['direct_edges']}, Inferred: {stats['inferred_edges']})")
    print(f"Reciprocal Pairs (Directed Cycles): {stats.get('reciprocal_pairs_count')} {stats.get('reciprocal_classification')}")
    print(f"Content Hash (Deterministic): {stats.get('content_hash')}")
    print(f"Connected Components: {stats['connected_components_count']} (Largest component: {stats['largest_component_size']} nodes)")
    print()

    print("--- Relationship Distribution (15 Canonical Types) ---")
    for rel, cnt in sorted(stats['relationship_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {rel:<28} : {cnt:>4}")
    print()

    print("--- Obligation Distribution ---")
    for ob, cnt in sorted(stats['obligation_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {ob:<28} : {cnt:>4}")
    print()

    print("--- Top In-Degree Hub Standards (Most Cited / Foundational) ---")
    for std, deg in stats['top_in_degree_hubs']:
        print(f"  {std:<35} : {deg:>3} citations")
    print()


def main():
    parser = argparse.ArgumentParser(description="StandSpec AI Standards Knowledge Graph Builder")
    parser.add_argument("--html-dir", "-d", default="data/raw/preview_html", help="Directory containing cached preview HTML files")
    parser.add_argument("--jsonl", "-j", nargs="+", default=None, help="Path(s) to standards.jsonl file(s). Supply multiple for unified multi-department graph.")
    parser.add_argument("--output", "-o", default="data/processed/standards_graph.json", help="Path to save output graph JSON")
    parser.add_argument("--top-hubs", type=int, default=15, help="Number of top hubs to display in report")

    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.jsonl:
        jsonl_paths = [Path(p) for p in args.jsonl]
        for jp in jsonl_paths:
            if not jp.exists():
                logger.error(f"JSONL file not found: {jp}")
                sys.exit(1)
        record_count = 0
        for jp in jsonl_paths:
            with open(jp, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    identity = rec.get("identity", {})
                    if identity.get("standard_designation") or rec.get("standard_number") or rec.get("normalized_designation"):
                        record_count += 1
        graph = build_graph_from_jsonl(jsonl_paths)
        if record_count > 0 and graph["nodes_count"] == 0:
            logger.error(
                f"HARD FAIL: {record_count} valid records in JSONL but graph has 0 nodes. "
                f"This indicates a V1.2 schema/graph-builder incompatibility."
            )
            sys.exit(1)
        graph_valid, graph_errors = validate_graph(graph)
        if not graph_valid:
            for err in graph_errors[:15]:
                logger.error(f"Graph validation: {err}")
            logger.error(f"Graph schema validation failed with {len(graph_errors)} errors. Aborting.")
            sys.exit(1)
        logger.info(f"Graph schema validation passed ({graph['nodes_count']} nodes, {graph['edges_count']} edges).")
    else:
        html_dir = Path(args.html_dir)
        if not html_dir.exists():
            logger.error(f"HTML directory not found: {html_dir}")
            sys.exit(1)
        logger.info("Building knowledge graph from cached BIS preview HTML...")
        graph = build_graph_from_html(html_dir)
        graph_valid, graph_errors = validate_graph(graph)
        if not graph_valid:
            for err in graph_errors[:15]:
                logger.error(f"Graph validation: {err}")
            logger.error(f"Graph schema validation failed with {len(graph_errors)} errors. Aborting.")
            sys.exit(1)

    logger.info(f"Writing knowledge graph to {out_path}...")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    stats = compute_graph_statistics(graph)
    print_graph_report(stats)
    logger.info("Graph construction complete!")


if __name__ == "__main__":
    main()
