"""
StandSpec AI — Tender PDF Ingestion & Clause Extractor
Extracts technical specifications, Bill of Quantities (BOQ), and Schedule of Requirements
from tender documents for compliance cross-referencing against Indian Standards (BIS).
"""

import io
import re
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pypdf

from src.extraction.requirement_extractor import RequirementExtractor


class TenderPDFExtractor:
    """
    Parses PDF tender specifications, extracts metadata,
    and segments technical specifications into individual auditable items.
    """

    def __init__(self, extractor: Optional[RequirementExtractor] = None):
        self.extractor = extractor or RequirementExtractor()

    def extract_from_bytes(self, pdf_bytes: bytes, filename: str = "tender.pdf") -> Dict[str, Any]:
        """Reads PDF bytes and returns structured document analysis."""
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        num_pages = len(reader.pages)

        pages_text: List[Dict[str, Any]] = []
        full_text_list: List[str] = []

        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages_text.append({"page_number": idx, "text": text})
            full_text_list.append(text)

        all_text = "\n\n".join(full_text_list)
        metadata = self._extract_metadata(all_text, filename)
        clauses = self._segment_clauses(pages_text)

        return {
            "document_id": f"DOC_{uuid.uuid4().hex[:10].upper()}",
            "filename": filename,
            "page_count": num_pages,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "tender_metadata": metadata,
            "total_extracted_clauses": len(clauses),
            "clauses": clauses,
        }

    def _extract_metadata(self, text: str, filename: str) -> Dict[str, Any]:
        """Extracts tender number, issuing authority, and dates from document header text."""
        # Tender No. patterns
        tender_no_patterns = [
            r'(?:tender\s*(?:no\.?|ref|notice\s*no\.?)|nit\s*(?:no\.?)|bid\s*no\.?)\s*[:\-]?\s*([A-Za-z0-9\-\/\_]+)',
            r'(?:gem\s*bid\s*(?:no\.?))\s*[:\-]?\s*([A-Za-z0-9\-\/\_]+)',
        ]
        tender_id = None
        for pat in tender_no_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                tender_id = m.group(1).strip()
                break
        if not tender_id:
            tender_id = filename.replace(".pdf", "")

        # Issuing Authority patterns
        authorities = [
            "Central Public Works Department (CPWD)",
            "CPWD",
            "National Thermal Power Corporation (NTPC)",
            "NTPC",
            "Bharat Heavy Electricals Limited (BHEL)",
            "BHEL",
            "Indian Railways",
            "Military Engineer Services (MES)",
            "National Highways Authority of India (NHAI)",
            "Government e-Marketplace (GeM)",
            "Delhi Metro Rail Corporation (DMRC)",
            "State Electricity Board",
            "Public Works Department (PWD)",
        ]
        detected_authority = "Public Procurement Entity"
        for auth in authorities:
            if re.search(r'\b' + re.escape(auth) + r'\b', text, re.IGNORECASE):
                detected_authority = auth
                break

        # Tender Date pattern
        date_match = re.search(
            r'(?:dated?|date\s*of\s*issue|published\s*on)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
            text,
            re.IGNORECASE,
        )
        tender_date = date_match.group(1).strip() if date_match else datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Title extraction (heuristic: first non-empty lines)
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 15]
        title = lines[0] if lines else "Tender Procurement Specification"
        if len(title) > 120:
            title = title[:117] + "..."

        return {
            "tender_id": tender_id,
            "title": title,
            "issuing_authority": detected_authority,
            "publish_date": tender_date,
        }

    def _segment_clauses(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Segments pages into individual technical procurement line items."""
        clauses: List[Dict[str, Any]] = []
        item_counter = 1

        # Patterns that indicate a technical line-item or specification paragraph
        item_pattern = re.compile(
            r'(?:(?:item|sl\.?|s\.no\.?|clause|section)\s*(?:no\.?)?\s*(\d+(?:\.\d+)*)|(?:^\s*(\d+)[\.\)]))\s+(.+)',
            re.IGNORECASE | re.MULTILINE,
        )

        # Technical keywords to filter out general contractual/boilerplate clauses
        tech_keywords = [
            "supply", "cable", "pipe", "transformer", "switchgear", "cement", "concrete",
            "conductor", "voltage", "insulation", "diameter", "grade", "conforming to",
            "is:", "is :", "is-", "is ", "specification", "feeder", "earthing", "meter",
            "steel", "rebar", "door", "window", "fitting", "valves", "aggregate", "panel"
        ]

        for p in pages:
            page_no = p["page_number"]
            page_text = p["text"]
            lines = page_text.split("\n")

            current_clause_num = None
            current_clause_text = []

            for line in lines:
                l_strip = line.strip()
                if not l_strip:
                    continue

                m = item_pattern.match(l_strip)
                if m:
                    # Flush previous clause if technical
                    if current_clause_text:
                        full_clause = " ".join(current_clause_text).strip()
                        if any(kw in full_clause.lower() for kw in tech_keywords) and len(full_clause) > 25:
                            clauses.append(self._format_clause(item_counter, current_clause_num, full_clause, page_no))
                            item_counter += 1
                        current_clause_text = []

                    num = m.group(1) or m.group(2)
                    current_clause_num = num
                    current_clause_text.append(m.group(3).strip())
                else:
                    if current_clause_text:
                        current_clause_text.append(l_strip)
                    elif any(kw in l_strip.lower() for kw in tech_keywords) and len(l_strip) > 30:
                        # Direct unnumbered technical line
                        current_clause_num = str(item_counter)
                        current_clause_text.append(l_strip)

            if current_clause_text:
                full_clause = " ".join(current_clause_text).strip()
                if any(kw in full_clause.lower() for kw in tech_keywords) and len(full_clause) > 25:
                    clauses.append(self._format_clause(item_counter, current_clause_num, full_clause, page_no))
                    item_counter += 1

        # Fallback: If no structured numbered items were found, chunk by paragraph
        if not clauses:
            for p in pages:
                paragraphs = [par.strip() for par in p["text"].split("\n\n") if len(par.strip()) > 35]
                for par in paragraphs:
                    if any(kw in par.lower() for kw in tech_keywords):
                        clauses.append(self._format_clause(item_counter, str(item_counter), par, p["page_number"]))
                        item_counter += 1

        return clauses

    def _format_clause(self, counter: int, ref_num: Optional[str], text: str, page_no: int) -> Dict[str, Any]:
        """Formats and extracts entities from an individual clause."""
        ref = f"Item {ref_num or counter}"
        req_res = self.extractor.extract(text, query_id=f"ITEM_{counter:03d}")
        reqs = req_res.get("requirements", {})

        # Domain heuristic
        text_lower = text.lower()
        if any(w in text_lower for w in ["cable", "voltage", "kv", "transformer", "switchgear", "conductor", "meter", "current", "breaker"]):
            domain = "Electrotechnical (ETD)"
        elif any(w in text_lower for w in ["pipe", "cement", "concrete", "steel", "rebar", "door", "window", "aggregate", "sand", "brick"]):
            domain = "Civil Engineering (CED)"
        else:
            domain = "General Procurement"

        # Check for cited standard
        cited_match = re.search(r'\b(IS\s*\d+(?:\s*(?:Part|\()\s*\d+[^\)]*\)?)?(?::\d{4})?)\b', text, re.IGNORECASE)
        cited_standard = cited_match.group(1).strip() if cited_match else None

        extracted_summary: Dict[str, Any] = {}
        for k in ["product", "voltage", "material", "dimensions", "grade", "application", "installation"]:
            val = reqs.get(k)
            if isinstance(val, dict) and val.get("value"):
                extracted_summary[k] = val.get("normalization") or val.get("value")

        if cited_standard:
            extracted_summary["cited_standard"] = cited_standard

        return {
            "item_id": f"ITEM_{counter:03d}",
            "clause_reference": f"{ref} (Page {page_no})",
            "raw_text": text,
            "page_number": page_no,
            "domain": domain,
            "extracted_entities": extracted_summary,
            "cited_standard": cited_standard,
            "status": "PENDING_VERIFICATION",
        }
