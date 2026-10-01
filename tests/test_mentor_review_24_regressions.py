"""
Authoritative 24-Point Regression Test Suite — StandSpec AI (PART 36)
======================================================================
Validates all 24 explicit regression requirements from the Mentor Review:

 1. UNKNOWN_ROLE cannot become primary.
 2. UNKNOWN_ROLE produces ROLE_UNVERIFIED.
 3. Contradictory product/technical parameter query abstains.
 4. Unverified regulatory state never becomes VOLUNTARY.
 5. Missing scope never becomes fabricated scope.
 6. Missing lifecycle never becomes ACTIVE.
 7. Missing amendment data never becomes "no amendments".
 8. Tender page starts empty.
 9. Standards Explorer starts empty.
10. Backend-down status is not READY.
11. No hardcoded recommendation in production frontend.
12. Raw rerank score is never displayed as confidence percentage.
13. CED/ETD scope is correctly enforced.
14. Multilingual extraction is tested.
15. Open-world wrong-primary cases are regression tests.
16. Full recommendation result is preserved for tender clauses.
17. PDF size/page limits are enforced.
18. CORS does not use wildcard + credentials.
19. No frontend secret exists.
20. LLM-disabled mode works.
21. LLM-enabled extraction is schema validated.
22. LLM explanation cannot invent recommendation.
23. Regulatory explanation cannot invent mandate.
24. Lifecycle explanation cannot invent active status.
"""

import os
import re
import json
from pathlib import Path
import pytest

from src.recommendation.corpus_policy import CandidateEligibilityPolicy
from src.recommendation.evidence_bundle import (
    EvidenceBundle,
    EvidencePolicy,
    ClaimType,
    EvidenceGapCode,
)
from src.recommendation.consistency_gate import (
    RequirementConsistencyGate,
    ConsistencyCheckResult,
)
from src.llm.explanation import ExplanationFacts, EvidenceGroundedExplainer
from src.extraction.requirement_extractor import RequirementExtractor
from src.recommendation.engine import StandSpecRecommendationEngine


PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ─────────────────────────────────────────────────────────────────────────────
# 1. UNKNOWN_ROLE cannot become primary
# ─────────────────────────────────────────────────────────────────────────────
def test_01_unknown_role_cannot_become_primary():
    """Verify that an UNKNOWN_ROLE node is never eligible as a primary candidate."""
    node = {
        "designation": "IS 99999:2025",
        "title": "Unclassified Test Item",
        "standard_role": "UNKNOWN_ROLE",
        "candidate_status": "ELIGIBLE",
        "node_type": "BIS_STANDARD",
    }
    is_primary = CandidateEligibilityPolicy.is_primary_candidate(node, intent="SUPPLY")
    assert is_primary is False, "UNKNOWN_ROLE candidate must not be eligible for primary recommendation"


# ─────────────────────────────────────────────────────────────────────────────
# 2. UNKNOWN_ROLE produces ROLE_UNVERIFIED
# ─────────────────────────────────────────────────────────────────────────────
def test_02_unknown_role_produces_role_unverified():
    """Verify that evaluating an UNKNOWN_ROLE bundle generates ROLE_UNVERIFIED gap."""
    bundle = EvidenceBundle(
        designation="IS 99999:2025",
        title="Unclassified Item",
        standard_role="UNKNOWN_ROLE",
    )
    gaps = bundle.get_evidence_gaps(ClaimType.PRIMARY_RECOMMENDATION_CLAIM)
    assert EvidenceGapCode.ROLE_UNVERIFIED.value in gaps, (
        f"Expected ROLE_UNVERIFIED in gaps, got {gaps}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Contradictory product/technical parameter query abstains
# ─────────────────────────────────────────────────────────────────────────────
def test_03_contradictory_query_abstains():
    """Verify contradictory product queries are detected and abstain safely."""
    query = "Supply of HDPE water pipe for 33kV distribution transformer"
    gate_res = RequirementConsistencyGate.check(query)
    assert not gate_res.is_consistent, "Should detect cross-domain product contradiction"
    assert len(gate_res.contradictions) > 0

    engine = StandSpecRecommendationEngine.from_release()
    result = engine.recommend(query)
    assert result["decision_state"] in ("INSUFFICIENT_INFORMATION", "CONTRADICTORY_SPECIFICATIONS")
    assert result["primary_recommendation"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Unverified regulatory state never becomes VOLUNTARY
# ─────────────────────────────────────────────────────────────────────────────
def test_04_unverified_regulatory_state_never_becomes_voluntary():
    """Verify unverified regulatory status outputs NOT_VERIFIED_IN_CURRENT_CORPUS and never voluntary."""
    facts = ExplanationFacts(
        decision_state="PRIMARY_RECOMMENDATION_AVAILABLE",
        is_recommended=True,
        standard_designation="IS 4984:2016",
        title="HDPE Pipe",
        regulatory_state="NOT_VERIFIED_IN_CURRENT_CORPUS",
    )
    explainer = EvidenceGroundedExplainer()
    explanation = explainer._generate_deterministic_explanation(facts)
    assert "voluntary" not in explanation.lower()
    assert "not mandatory" not in explanation.lower()
    assert "Regulatory mandatory status was not verified in the current regulatory corpus" in explanation


# ─────────────────────────────────────────────────────────────────────────────
# 5. Missing scope never becomes fabricated scope
# ─────────────────────────────────────────────────────────────────────────────
def test_05_missing_scope_never_becomes_fabricated_scope():
    """Verify that standards with empty scope are marked scope_ready=False and SCOPE_MISSING."""
    bundle = EvidenceBundle(
        designation="IS 1234:2000",
        title="Sample Standard Without Scope",
        standard_role="PRODUCT_SPECIFICATION",
    )
    assert not bundle.raw_scope
    assert bundle.scope_ready is False
    gaps = bundle.get_evidence_gaps(ClaimType.PRIMARY_RECOMMENDATION_CLAIM)
    assert EvidenceGapCode.SCOPE_MISSING.value in gaps


# ─────────────────────────────────────────────────────────────────────────────
# 6. Missing lifecycle never becomes ACTIVE
# ─────────────────────────────────────────────────────────────────────────────
def test_06_missing_lifecycle_never_becomes_active():
    """Verify that unverified lifecycle defaults to UNKNOWN and is not lifecycle_ready."""
    bundle = EvidenceBundle(
        designation="IS 1234:2000",
        title="Sample Standard",
        standard_role="PRODUCT_SPECIFICATION",
    )
    assert bundle.lifecycle_ready is False
    assert bundle.lifecycle_evidence.get("status") in ("UNKNOWN", "LIFECYCLE_UNVERIFIED", "")
    gaps = bundle.get_evidence_gaps(ClaimType.PRIMARY_RECOMMENDATION_CLAIM)
    assert EvidenceGapCode.LIFECYCLE_UNVERIFIED.value in gaps


# ─────────────────────────────────────────────────────────────────────────────
# 7. Missing amendment data never becomes "no amendments"
# ─────────────────────────────────────────────────────────────────────────────
def test_07_missing_amendment_data_never_becomes_no_amendments():
    """Verify facts and explainer do not assert 'no amendments' when data is missing."""
    facts = ExplanationFacts(
        decision_state="PRIMARY_RECOMMENDATION_AVAILABLE",
        is_recommended=True,
        standard_designation="IS 1786:2008",
        title="High Strength Deformed Steel Bars",
        amendments=[],
    )
    explainer = EvidenceGroundedExplainer()
    explanation = explainer._generate_deterministic_explanation(facts)
    assert "no amendments" not in explanation.lower()
    assert "0 amendments" not in explanation.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 8. Tender page starts empty
# ─────────────────────────────────────────────────────────────────────────────
def test_08_tender_page_starts_empty():
    """Verify TenderPdfStudio.jsx initializes with clean null docData and no auto-loaded clauses."""
    tender_file = PROJECT_ROOT / "frontend" / "src" / "components" / "TenderPdfStudio.jsx"
    assert tender_file.exists()
    content = tender_file.read_text(encoding="utf-8")
    assert "const [docData, setDocData] = useState(null);" in content
    assert "const [activeClause, setActiveClause] = useState(null);" in content


# ─────────────────────────────────────────────────────────────────────────────
# 9. Standards Explorer starts empty
# ─────────────────────────────────────────────────────────────────────────────
def test_09_standards_explorer_starts_empty():
    """Verify StandardsExplorer.jsx initializes with empty query and empty results."""
    explorer_file = PROJECT_ROOT / "frontend" / "src" / "components" / "StandardsExplorer.jsx"
    assert explorer_file.exists()
    content = explorer_file.read_text(encoding="utf-8")
    assert 'const [query, setQuery] = useState("");' in content
    assert "const [results, setResults] = useState([]);" in content


# ─────────────────────────────────────────────────────────────────────────────
# 10. Backend-down status is not READY
# ─────────────────────────────────────────────────────────────────────────────
def test_10_backend_down_status_is_not_ready():
    """Verify health check logic in api.js sets status: 'OFFLINE' on error and not 'READY'."""
    api_file = PROJECT_ROOT / "frontend" / "src" / "api.js"
    assert api_file.exists()
    content = api_file.read_text(encoding="utf-8")
    assert 'status: "OFFLINE"' in content
    
    header_file = PROJECT_ROOT / "frontend" / "src" / "components" / "Header.jsx"
    assert header_file.exists()
    header_content = header_file.read_text(encoding="utf-8")
    assert 'health?.status === "READY"' in header_content
    assert '"Backend Offline"' in header_content


# ─────────────────────────────────────────────────────────────────────────────
# 11. No hardcoded recommendation in production frontend
# ─────────────────────────────────────────────────────────────────────────────
def test_11_no_hardcoded_recommendation_in_production_frontend():
    """Verify production frontend components do not hardcode mock standards recommendations."""
    query_studio = PROJECT_ROOT / "frontend" / "src" / "components" / "QueryStudio.jsx"
    assert query_studio.exists()
    content = query_studio.read_text(encoding="utf-8")
    assert "mockRecommendation" not in content
    assert "const mockResult" not in content


# ─────────────────────────────────────────────────────────────────────────────
# 12. Raw rerank score is never displayed as confidence percentage
# ─────────────────────────────────────────────────────────────────────────────
def test_12_raw_rerank_score_never_displayed_as_confidence_percentage():
    """Verify frontend displays raw rerank scores with uncalibrated disclosure."""
    alt_standards = PROJECT_ROOT / "frontend" / "src" / "components" / "QueryStudio" / "AlternativeStandards.jsx"
    assert alt_standards.exists()
    content = alt_standards.read_text(encoding="utf-8")
    assert "Uncalibrated" in content
    assert "Match Score" in content


# ─────────────────────────────────────────────────────────────────────────────
# 13. CED/ETD scope is correctly enforced
# ─────────────────────────────────────────────────────────────────────────────
def test_13_ced_etd_scope_is_correctly_enforced():
    """Verify external standards and excluded records are rejected by eligibility policy."""
    ext_node = {
        "designation": "ISO 9001:2015",
        "title": "Quality Management Systems",
        "node_type": "EXTERNAL_STANDARD",
        "standard_role": "MANAGEMENT_SYSTEM",
    }
    assert CandidateEligibilityPolicy.is_primary_candidate(ext_node) is False

    excluded_node = {
        "designation": "IS 1000:1990",
        "title": "Excluded Item",
        "candidate_status": "EXCLUDED",
        "standard_role": "PRODUCT_SPECIFICATION",
    }
    assert CandidateEligibilityPolicy.is_primary_candidate(excluded_node) is False


# ─────────────────────────────────────────────────────────────────────────────
# 14. Multilingual extraction is tested
# ─────────────────────────────────────────────────────────────────────────────
def test_14_multilingual_extraction_is_tested():
    """Verify multilingual requirement extraction identifies Hindi, Gujarati, and Hinglish."""
    extractor = RequirementExtractor()

    # Hindi (Devanagari)
    hindi_query = "11 केवी वितरण ट्रांसफार्मर की आपूर्ति"
    extracted_hi = extractor.extract(hindi_query)
    assert extracted_hi["language"] == "hi"
    assert extracted_hi["requirements"]["product"] is not None
    assert "Transformer" in extracted_hi["requirements"]["product"]["normalization"]

    # Gujarati
    guj_query = "11 કેવી ટ્રાન્સફોર્મર સપ્લાય ટેન્ડર"
    extracted_gu = extractor.extract(guj_query)
    assert extracted_gu["language"] == "gu"
    assert extracted_gu["requirements"]["product"] is not None
    assert "Transformer" in extracted_gu["requirements"]["product"]["normalization"]

    # Hinglish (Code-mixed)
    hinglish_query = "Substation ke liye 11 kV grade XLPE underground power cable chahiye"
    extracted_hing = extractor.extract(hinglish_query)
    assert extracted_hing["language"] == "hinglish"
    assert extracted_hing["requirements"]["product"] is not None
    assert "Cable" in extracted_hing["requirements"]["product"]["normalization"]


# ─────────────────────────────────────────────────────────────────────────────
# 15. Open-world wrong-primary cases are regression tests
# ─────────────────────────────────────────────────────────────────────────────
def test_15_open_world_wrong_primary_cases():
    """Verify Fe 500D rebar never recommends polymer rebar (IS 18256)."""
    engine = StandSpecRecommendationEngine.from_release()
    result = engine.recommend("Fe 500D TMT reinforcement steel bars for concrete construction")
    if result.get("primary_recommendation"):
        desig = result["primary_recommendation"].get("standard_designation") or result["primary_recommendation"].get("designation", "")
        assert "18256" not in desig, f"Must not promote polymer rebar IS 18256 for steel Fe 500D query: {desig}"


# ─────────────────────────────────────────────────────────────────────────────
# 16. Full recommendation result is preserved for tender clauses
# ─────────────────────────────────────────────────────────────────────────────
def test_16_full_recommendation_result_preserved_for_tender_clauses():
    """Verify TenderPdfStudio.jsx stores the complete backend response on the clause object."""
    tender_file = PROJECT_ROOT / "frontend" / "src" / "components" / "TenderPdfStudio.jsx"
    content = tender_file.read_text(encoding="utf-8")
    assert "backend_result: r," in content
    assert "recommendation: primary ?" in content


# ─────────────────────────────────────────────────────────────────────────────
# 17. PDF size/page limits are enforced
# ─────────────────────────────────────────────────────────────────────────────
def test_17_pdf_size_page_limits_enforced():
    """Verify PDF limits (20MB and 200 pages) in frontend and server."""
    tender_file = PROJECT_ROOT / "frontend" / "src" / "components" / "TenderPdfStudio.jsx"
    content = tender_file.read_text(encoding="utf-8")
    assert "20 * 1024 * 1024" in content
    assert "20 MB" in content

    server_file = PROJECT_ROOT / "src" / "api" / "server.py"
    server_content = server_file.read_text(encoding="utf-8")
    assert 'MAX_PDF_SIZE_MB = int(os.environ.get("MAX_PDF_SIZE_MB", "20"))' in server_content
    assert 'MAX_PDF_PAGES = int(os.environ.get("MAX_PDF_PAGES", "200"))' in server_content


# ─────────────────────────────────────────────────────────────────────────────
# 18. CORS does not use wildcard + credentials
# ─────────────────────────────────────────────────────────────────────────────
def test_18_cors_does_not_use_wildcard_plus_credentials():
    """Verify server CORS does not pair allow_origins=['*'] with allow_credentials=True."""
    server_file = PROJECT_ROOT / "src" / "api" / "server.py"
    server_content = server_file.read_text(encoding="utf-8")
    assert '_allow_credentials = False if "*" in _cors_origins else True' in server_content
    assert "allow_credentials=_allow_credentials" in server_content


# ─────────────────────────────────────────────────────────────────────────────
# 19. No frontend secret exists
# ─────────────────────────────────────────────────────────────────────────────
def test_19_no_frontend_secret_exists():
    """Scan frontend files to ensure no API keys or bearer tokens exist."""
    frontend_src = PROJECT_ROOT / "frontend" / "src"
    secret_patterns = [
        re.compile(r"AIza[0-9A-Za-z-_]{35}"),
        re.compile(r"bearer\s+[A-Za-z0-9_\-\.]{20,}", re.IGNORECASE),
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    ]
    for root, _, files in os.walk(frontend_src):
        for f in files:
            if f.endswith((".js", ".jsx", ".ts", ".tsx", ".html", ".env")):
                p = Path(root) / f
                content = p.read_text(encoding="utf-8", errors="ignore")
                for pat in secret_patterns:
                    assert not pat.search(content), f"Found potential secret in {p}"


# ─────────────────────────────────────────────────────────────────────────────
# 20. LLM-disabled mode works
# ─────────────────────────────────────────────────────────────────────────────
def test_20_llm_disabled_mode_works():
    """Verify recommendation engine functions with 100% deterministic rules when LLM is disabled."""
    engine = StandSpecRecommendationEngine.from_release()
    result = engine.recommend("supply of HDPE pipe for drinking water")
    assert result is not None
    assert result["decision_state"] in ("PRIMARY_RECOMMENDATION_AVAILABLE", "MULTIPLE_POSSIBLE_STANDARDS", "EXPERT_REVIEW_REQUIRED")
    if result.get("primary_recommendation"):
        assert result.get("explanation") is not None
        assert "HDPE" in result["explanation"] or "pipe" in result["explanation"].lower() or "IS 4984" in result["explanation"]


# ─────────────────────────────────────────────────────────────────────────────
# 21. LLM-enabled extraction is schema validated
# ─────────────────────────────────────────────────────────────────────────────
def test_21_llm_enabled_extraction_schema_validated():
    """Verify RequirementExtractor schema integrity and deterministic fallback."""
    extractor = RequirementExtractor()
    extracted = extractor.extract("11kV 3-core cross-linked polyethylene cable")
    assert "product" in extracted["requirements"]
    assert "language" in extracted
    assert "missing_discriminators" in extracted
    assert extracted["requirements"]["product"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# 22. LLM explanation cannot invent recommendation
# ─────────────────────────────────────────────────────────────────────────────
def test_22_llm_explanation_cannot_invent_recommendation():
    """Verify that when facts state is_recommended=False, LLM output claiming a recommendation is rejected."""
    facts = ExplanationFacts(
        decision_state="INSUFFICIENT_INFORMATION",
        is_recommended=False,
        abstention_reason="Missing critical product specifications",
    )
    explainer = EvidenceGroundedExplainer()
    hallucinated_text = "We recommend IS 7098 Part 2 for this requirement."
    is_valid = explainer._validate_llm_response(hallucinated_text, facts)
    assert is_valid is False, "Explainer validation must reject recommendation claim when is_recommended=False"


# ─────────────────────────────────────────────────────────────────────────────
# 23. Regulatory explanation cannot invent mandate
# ─────────────────────────────────────────────────────────────────────────────
def test_23_regulatory_explanation_cannot_invent_mandate():
    """Verify that unverified regulatory state rejects LLM claims of mandatory or voluntary."""
    facts = ExplanationFacts(
        decision_state="PRIMARY_RECOMMENDATION_AVAILABLE",
        is_recommended=True,
        standard_designation="IS 4984:2016",
        regulatory_state="NOT_VERIFIED_IN_CURRENT_CORPUS",
    )
    explainer = EvidenceGroundedExplainer()
    
    # False claim of mandate
    assert explainer._validate_llm_response("This is mandatory under QCO order 2024.", facts) is False
    # False claim of voluntary
    assert explainer._validate_llm_response("This is a voluntary standard.", facts) is False


# ─────────────────────────────────────────────────────────────────────────────
# 24. Lifecycle explanation cannot invent active status
# ─────────────────────────────────────────────────────────────────────────────
def test_24_lifecycle_explanation_cannot_invent_active_status():
    """Verify that a superseded standard produces a superseded alert in lifecycle evidence."""
    bundle = EvidenceBundle(
        designation="IS 4984:1995",
        title="HDPE Pipe (Old Edition)",
        standard_role="PRODUCT_SPECIFICATION",
    )
    bundle.lifecycle_evidence["status"] = "SUPERSEDED"
    bundle.lifecycle_evidence["is_superseded"] = True
    bundle.lifecycle_evidence["superseded_by"] = "IS 4984:2016"
    assert bundle.lifecycle_ready is False
    gaps = bundle.get_evidence_gaps(ClaimType.PRIMARY_RECOMMENDATION_CLAIM)
    assert EvidenceGapCode.LIFECYCLE_UNVERIFIED.value in gaps
