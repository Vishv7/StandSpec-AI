"""
Preview page fetcher for BSB Edge.
Phase 3 of the BIS Standards Data Collector.

Conforms to Frozen V1.1 Collector Data Contract:
- Family-aware page identity verification (MATCH / MISMATCH / UNKNOWN)
- Candidate fallback rejection on identity mismatch
- UNKNOWN never silently promoted to success; marked review_required
- Strict rate limiting (minimum 1.0s sequential delay)
- Exponential backoff retry on transient errors
- Raw HTML response caching
"""

import time
import re
import logging
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from src.preview_id import parse_standard_identity, KNOWN_FAMILIES

logger = logging.getLogger(__name__)

# ── Configuration ──
BASE_URL = "https://standardsbis.bsbedge.com/BIS_Preview.aspx"
MIN_DELAY_SECONDS = 1.0          # Minimum delay between requests
MAX_RETRIES = 3                  # Max retry attempts
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
REQUEST_TIMEOUT = 30             # seconds

# Polite User-Agent
USER_AGENT = "BIS-Standards-Collector/1.1 (Research; StandSpec-AI-SIH26108)"


class PreviewFetcher:
    """
    Fetches BSB Edge preview pages with rate limiting, retry/backoff,
    identity verification, and raw caching.
    """
    
    def __init__(self, cache_dir: str | Path = "data/raw/preview_html"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._last_request_time = time.time()
        
    def _rate_limit(self):
        """Enforce minimum delay between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < MIN_DELAY_SECONDS:
            wait = MIN_DELAY_SECONDS - elapsed
            logger.debug(f"Rate limiting: waiting {wait:.2f}s")
            time.sleep(wait)
            
    def _get_cache_path(self, preview_id: str) -> Path:
        """Get the cache file path for a given preview ID."""
        return self.cache_dir / f"{preview_id}.html"
        
    def is_cached(self, preview_id: str) -> bool:
        """Check if a preview page is cached locally with valid content."""
        cache_path = self._get_cache_path(preview_id)
        if not (cache_path.exists() and cache_path.stat().st_size > 0):
            return False
        html = cache_path.read_text(encoding="utf-8", errors="replace")
        return self._sanity_check(html, preview_id)
        
    def get_cached_html(self, preview_id: str) -> str | None:
        """Read cached HTML from disk if valid, else None."""
        cache_path = self._get_cache_path(preview_id)
        if cache_path.exists() and cache_path.stat().st_size > 0:
            html = cache_path.read_text(encoding="utf-8", errors="replace")
            if self._sanity_check(html, preview_id):
                return html
        return None
        
    def extract_page_identity(self, html: str) -> dict | None:
        """
        Extract the standard identity from the preview page header.
        Looks for the top bold element containing standard designation.
        """
        if not html:
            return None
            
        soup = BeautifulSoup(html, "lxml")
        body = soup.body if soup.body else soup
        
        # Look for header elements with concise text length near top of document
        # Excludes broad container tags like <div> which wrap whole sections or references
        for el in body.find_all(['p', 'b', 'strong', 'h1', 'h2', 'h3', 'span']):
            text = el.get_text(strip=True)
            if not text or len(text) < 5 or len(text) > 300:
                continue
                
            best_match = None
            best_pos = float('inf')
            
            for family in KNOWN_FAMILIES:
                pattern = r'\b' + re.escape(family) + r'\s+(\d+[\w.-]*)(?:\s*:\s*Part\s*(\w+))?(?:\s*:\s*Sec(?:tion)?\s*(\w+))?(?:\s*:\s*(\d{4}))?'
                m = re.search(pattern, text, re.IGNORECASE)
                if m and m.start() < best_pos:
                    base = m.group(1)
                    part = m.group(2)
                    sec = m.group(3)
                    year = m.group(4)
                    
                    # Also handle parens format e.g. "IS 302 (Part 2/Sec 16):2026"
                    m_parens = re.search(
                        r'\b' + re.escape(family) + r'\s+(\d+[\w.-]*)(?:\s*\(\s*Part\s*(\w+)(?:\s*/\s*Sec(?:tion)?\s*(\w+))?\s*\))?(?:\s*:\s*(\d{4}))?',
                        text, re.IGNORECASE
                    )
                    if m_parens and (m_parens.group(2) or m_parens.group(3)):
                        base = m_parens.group(1)
                        part = m_parens.group(2)
                        sec = m_parens.group(3)
                        year = m_parens.group(4) or year
                        
                    desig_parts = [family, f" {base}"]
                    if part and sec:
                        desig_parts.append(f" (Part {part}/Sec {sec})")
                    elif part:
                        desig_parts.append(f" (Part {part})")
                    if year:
                        desig_parts.append(f":{year}")
                    normalized_desig = "".join(desig_parts)
                    
                    best_pos = m.start()
                    best_match = {
                        "family": family,
                        "base_number": base,
                        "part": part,
                        "section": sec,
                        "year": year,
                        "header_text": text[:200],
                        "normalized_designation": normalized_desig,
                        "verification_method": "header_parser",
                    }
                    
            if best_match:
                return best_match
        return None
        
    def verify_page_identity(self, requested: dict, page_html: str) -> tuple[str, str | None, dict | None]:
        """
        Verify whether the page HTML corresponds to the requested standard identity.
        
        V1.2 identity match enum:
            "match"                    — family, base, part, section, year all match
            "match_version_uncertain"  — family/base/part/section match, but years differ
            "mismatch"                 — structural mismatch (different standard)
            "unknown"                  — could not extract identity from page
        
        CRITICAL: MATCH_VERSION_UNCERTAIN pages must NOT become canonical verified sources.
        Their Scope/References must NOT be treated as verified evidence without review.
        
        Returns:
            (status, reason, evidence_dict)
        """
        extracted = self.extract_page_identity(page_html)
        if not extracted:
            return "unknown", "No standard header found on preview page", None
            
        evidence = {
            "header_text": extracted["header_text"],
            "normalized_designation": extracted["normalized_designation"],
            "verification_method": "header_parser",
            "requested_year": requested.get("year") if requested else None,
            "page_year": extracted.get("year"),
            "year_match": None,  # set below
            "year_verification": None,  # set below
        }
        
        if not requested:
            evidence["year_match"] = True
            evidence["year_verification"] = "not_checked"
            return "match_version_verified", None, evidence
            
        req_fam = (requested.get("family") or "").upper().replace(" ", "")
        page_fam = (extracted.get("family") or "").upper().replace(" ", "")
        
        # 1. Family check (e.g. IS vs IS/IEC vs SP)
        if req_fam and page_fam and req_fam != page_fam:
            return "mismatch", f"Family mismatch: requested '{requested.get('family')}', got '{extracted.get('family')}'", evidence
            
        # 2. Base number check (e.g. 19901 vs 19897)
        req_base = str(requested.get("base_number") or "").strip()
        page_base = str(extracted.get("base_number") or "").strip()
        if req_base and page_base and req_base != page_base:
            return "mismatch", f"Base number mismatch: requested '{req_base}', got '{page_base}'", evidence
            
        # 3. Part check (e.g. Part 1 vs Part 2 vs unparted)
        req_part = str(requested.get("part") or "") if requested.get("part") is not None else None
        page_part = str(extracted.get("part") or "") if extracted.get("part") is not None else None
        if req_part != page_part:
            return "mismatch", f"Part mismatch: requested Part '{req_part}', got Part '{page_part}'", evidence
            
        # 4. Section check (e.g. Sec 16 vs Sec 21 vs unsectioned)
        req_sec = str(requested.get("section") or "") if requested.get("section") is not None else None
        page_sec = str(extracted.get("section") or "") if extracted.get("section") is not None else None
        if req_sec != page_sec:
            return "mismatch", f"Section mismatch: requested Sec '{req_sec}', got Sec '{page_sec}'", evidence
        
        # 5. A8: Year check — semantic version verification
        req_year = str(requested.get("year") or "").strip() if requested.get("year") else None
        page_year = str(extracted.get("year") or "").strip() if extracted.get("year") else None
        
        if req_year and page_year and req_year != page_year:
            # Years differ — this is version-uncertain, NOT a simple warning
            evidence["year_match"] = False
            evidence["year_verification"] = "uncertain"
            return (
                "match_version_uncertain",
                f"Year mismatch: requested '{req_year}', page shows '{page_year}'. "
                f"Different editions may have different scopes and references.",
                evidence
            )
        elif req_year and page_year and req_year == page_year:
            evidence["year_match"] = True
            evidence["year_verification"] = "verified"
            return "match_version_verified", None, evidence
        elif not req_year or not page_year:
            evidence["year_match"] = None
            evidence["year_verification"] = "incomplete"
            return (
                "match_identity_only_version_uncertain",
                f"Year missing from {'requested identity' if not req_year else 'preview page'}. "
                f"Standard base identity matches, but version cannot be verified.",
                evidence
            )
        
        return "match_version_verified", None, evidence

        
    def fetch(self, preview_id: str, force: bool = False) -> dict:
        """Fetch a single preview page by preview ID."""
        url = f"{BASE_URL}?id={preview_id}"
        cache_path = self._get_cache_path(preview_id)
        
        if not force and cache_path.exists() and cache_path.stat().st_size > 0:
            html = cache_path.read_text(encoding="utf-8", errors="replace")
            content_valid = self._sanity_check(html, preview_id)
            if content_valid:
                logger.debug(f"Cache hit for {preview_id}")
                return {
                    "preview_id": preview_id,
                    "url": url,
                    "status": "cached",
                    "http_status": 200,
                    "html": html,
                    "cache_path": str(cache_path),
                    "error": None,
                    "content_valid": True,
                }
            else:
                logger.info(f"Cache hit for {preview_id} but content is invalid/empty shell")
                return {
                    "preview_id": preview_id,
                    "url": url,
                    "status": "partial_success",
                    "http_status": 200,
                    "html": html,
                    "cache_path": str(cache_path),
                    "error": "Empty preview shell page",
                    "content_valid": False,
                }
                
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            self._rate_limit()
            try:
                logger.info(f"Fetching {preview_id} (attempt {attempt}/{MAX_RETRIES})")
                self._last_request_time = time.time()
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                
                if response.status_code == 200:
                    html = response.text
                    content_valid = self._sanity_check(html, preview_id)
                    if content_valid:
                        cache_path.write_text(html, encoding="utf-8")
                        logger.info(f"Cached {preview_id} -> {cache_path}")
                    else:
                        logger.warning(f"Response for {preview_id} has no content -- not caching")
                        
                    return {
                        "preview_id": preview_id,
                        "url": url,
                        "status": "success" if content_valid else "partial_success",
                        "http_status": 200,
                        "html": html,
                        "cache_path": str(cache_path),
                        "error": None if content_valid else "Empty preview shell page",
                        "content_valid": content_valid,
                    }
                elif response.status_code in RETRY_STATUS_CODES:
                    wait = 2 ** attempt
                    last_error = f"HTTP {response.status_code}"
                    logger.warning(f"Retryable error for {preview_id}: HTTP {response.status_code}, waiting {wait}s")
                    time.sleep(wait)
                    continue
                else:
                    last_error = f"HTTP {response.status_code}"
                    logger.error(f"Non-retryable error for {preview_id}: HTTP {response.status_code}")
                    break
            except requests.exceptions.RequestException as e:
                wait = 2 ** attempt
                last_error = str(e)
                logger.warning(f"Request exception for {preview_id}: {e}, waiting {wait}s")
                time.sleep(wait)
                continue
                
        return {
            "preview_id": preview_id,
            "url": url,
            "status": "failed",
            "http_status": None,
            "html": None,
            "cache_path": str(cache_path),
            "error": last_error,
            "content_valid": False,
        }
        
    def fetch_with_fallback(self, candidate_ids: list[str], requested_identity: dict = None, force: bool = False) -> dict:
        """
        Fetch a preview page by evaluating candidate IDs with family-aware identity verification.
        
        V1.2 identity handling:
        - MATCH: Accept immediately.
        - MATCH_VERSION_UNCERTAIN: Hold for review — years differ, cannot be canonical.
        - MISMATCH: Reject, try next candidate.
        - UNKNOWN: Hold for review if no MATCH found.
        
        Priority: MATCH > MATCH_VERSION_UNCERTAIN > UNKNOWN > FAILED
        """
        if not candidate_ids:
            return {
                "requested_preview_id": None,
                "matched_preview_id": None,
                "preview_url": None,
                "attempted_urls": [],
                "http_status": None,
                "fetch_status": "failed",
                "identity_match": "unknown",
                "page_identity_evidence": None,
                "html": None,
                "cache_path": None,
                "content_valid": False,
                "error": "No candidate preview IDs provided",
                "warnings": ["No candidate IDs"],
            }
            
        attempted_urls = []
        version_uncertain_result = None
        unknown_candidate_result = None
        
        for i, cand_id in enumerate(candidate_ids):
            cand_url = f"{BASE_URL}?id={cand_id}"
            attempted_urls.append(cand_url)
            
            fetch_res = self.fetch(cand_id, force=force)
            if not fetch_res.get("content_valid"):
                logger.info(f"Candidate '{cand_id}' returned empty/invalid page -- trying next")
                continue
                
            html = fetch_res.get("html", "")
            id_status, reason, evidence = self.verify_page_identity(requested_identity, html)
            
            if id_status in ("match_version_verified", "match"):
                if i > 0:
                    logger.info(f"Fallback candidate '{cand_id}' succeeded with verified MATCH")
                return {
                    "requested_preview_id": candidate_ids[0],
                    "matched_preview_id": cand_id,
                    "preview_url": cand_url,
                    "attempted_urls": attempted_urls,
                    "http_status": fetch_res.get("http_status", 200),
                    "fetch_status": "success",
                    "identity_match": "match_version_verified",
                    "page_identity_evidence": evidence,
                    "html": html,
                    "cache_path": fetch_res.get("cache_path"),
                    "content_valid": True,
                    "error": None,
                    "warnings": [f"Fallback candidate '{cand_id}' used"] if i > 0 else [],
                }
            elif id_status in ("match_version_uncertain", "match_identity_only_version_uncertain"):
                # A8: Hold version-uncertain result — prefer MATCH if later candidate matches
                logger.info(f"Candidate '{cand_id}' has VERSION UNCERTAIN identity ({id_status}): {reason}")
                if not version_uncertain_result:
                    version_uncertain_result = {
                        "requested_preview_id": candidate_ids[0],
                        "matched_preview_id": cand_id,
                        "preview_url": cand_url,
                        "attempted_urls": attempted_urls,
                        "http_status": fetch_res.get("http_status", 200),
                        "fetch_status": "review_required",
                        "identity_match": id_status,
                        "page_identity_evidence": evidence,
                        "html": html,
                        "cache_path": fetch_res.get("cache_path"),
                        "content_valid": True,
                        "error": None,
                        "warnings": [f"Version uncertain: {reason}"],
                    }
                continue
            elif id_status == "mismatch":
                logger.warning(f"Candidate '{cand_id}' REJECTED due to identity mismatch: {reason}")
                continue
            else:  # unknown
                logger.info(f"Candidate '{cand_id}' has UNKNOWN identity: {reason}")
                if not unknown_candidate_result:
                    unknown_candidate_result = {
                        "requested_preview_id": candidate_ids[0],
                        "matched_preview_id": cand_id,
                        "preview_url": cand_url,
                        "attempted_urls": attempted_urls,
                        "http_status": fetch_res.get("http_status", 200),
                        "fetch_status": "review_required",
                        "identity_match": "unknown",
                        "page_identity_evidence": evidence,
                        "html": html,
                        "cache_path": fetch_res.get("cache_path"),
                        "content_valid": True,
                        "error": None,
                        "warnings": [f"Identity unknown: {reason}"],
                    }
                    
        # Priority: version_uncertain > unknown > failed
        if version_uncertain_result:
            return version_uncertain_result
        if unknown_candidate_result:
            return unknown_candidate_result
            
        return {
            "requested_preview_id": candidate_ids[0],
            "matched_preview_id": None,
            "preview_url": f"{BASE_URL}?id={candidate_ids[0]}",
            "attempted_urls": attempted_urls,
            "http_status": None,
            "fetch_status": "failed",
            "identity_match": "unknown",
            "page_identity_evidence": None,
            "html": None,
            "cache_path": None,
            "content_valid": False,
            "error": "All preview ID candidates failed content check or identity verification",
            "warnings": ["Candidates exhausted"],
        }
        
    def _sanity_check(self, html: str, preview_id: str) -> bool:
        """
        Sanity check that fetched HTML has real standard content, not an empty error shell.
        
        Rejects:
        - empty HTML or extremely short content (< 100 chars)
        - known error shell text (e.g. "Standard not found", "No preview available", "Empty shell page")
        - empty error bodies
        
        Accepts:
        - pages containing identifiable standard designations (IS, SP, ISO, IEC)
        - pages containing key structural markers (SCOPE, FOREWORD, REFERENCES, ICS, Technical Committee)
        """
        if not html:
            return False
            
        stripped = html.strip()
        if len(stripped) < 100:
            return False

        # Reject generic empty shells
        html_lower = stripped.lower()
        if "empty shell page" in html_lower or "standard not found" in html_lower or "no preview available" in html_lower:
            return False

        # Check for structural standard content markers
        structural_markers = [
            "scope", "foreword", "national foreword", "references",
            "normative references", "ics ", "new standard", "technical committee",
            "department", "bureau of indian standards"
        ]
        has_structural_marker = any(m in html_lower for m in structural_markers)

        # Check for standard designation pattern
        has_standard_ident = bool(re.search(
            r'\b(?:IS/ISO/IEC|IS/IEC|IS/ISO|IS|ISO/IEC\s+GUIDE|ISO/IEC|ISO|IEC|SP)\s+\d+',
            stripped, re.IGNORECASE
        ))

        return has_structural_marker or has_standard_ident
        
    def close(self):
        """Close the HTTP session."""
        self.session.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
