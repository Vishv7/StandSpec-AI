"""
Exact Designation Intent Resolver — StandSpec AI (Phase P1-A)
Detects explicit Indian Standard / International Standard mentions in tender clauses,
normalizes designations to canonical hierarchy (Family -> Part -> Edition),
and ensures explicit user intent is prioritized over unguided semantic retrieval.

Design Law:
- Family (e.g. IS 7098)
   ├── Part 1 (Editions: 1988, 2012, ...)
   └── Part 2 (Editions: 1985, 2011, ...)
- IS 7098 Part 2:2011 -> exact edition
- IS 7098 Part 2      -> return Part 2 edition set (lifecycle resolves latest active edition)
- IS 7098             -> umbrella family query; NEVER silently select a random part
- IS 4984:2016        -> exact edition of single-part standard
- IS 4984             -> return edition set of single-part standard
"""

import re
from typing import Dict, Any, List, Optional, Tuple


DESIGNATION_REGEX = re.compile(
    r"\b(?:IS\s*/\s*IEC|IS\s*/\s*ISO|IS)\s*[:\-]?\s*(\d+)"
    r"(?:\s*[\(\[]?\s*[Pp]art\s*(\d+)[\)\]]?)?"
    r"(?:\s*[\/\-]\s*[Ss]ec(?:tion)?\s*(\d+))?"
    r"(?:\s*:\s*(\d{4}))?\b",
    re.IGNORECASE,
)


class DesignationResolver:
    """
    Detects and resolves exact/near-exact standard designations from tender queries
    with strict multi-tier hierarchy: Family -> Part -> Edition.
    """

    def __init__(self, standards_graph: Optional[dict] = None):
        self.standards_graph = standards_graph or {}
        # exact_map: "IS 7098 (PART 2):2011" -> node
        self.exact_map: Dict[str, dict] = {}
        # family_parts: base_number -> {part_key -> [nodes sorted by year desc]}
        self.family_parts: Dict[int, Dict[Optional[str], List[dict]]] = {}
        # family_sections: (base_number, part_str) -> {sec_str -> [nodes sorted by year desc]}
        self.family_sections: Dict[Tuple[int, Optional[str]], Dict[Optional[str], List[dict]]] = {}

        if standards_graph:
            self.index_graph(standards_graph)

    def index_graph(self, standards_graph: dict):
        """Index nodes into exact edition map and family-part-edition hierarchy."""
        self.standards_graph = standards_graph
        self.exact_map = {}
        self.family_parts = {}
        self.family_sections = {}

        for node in standards_graph.get("nodes", []):
            desig = node.get("designation")
            if not desig:
                continue

            desig_clean = desig.strip().upper()
            self.exact_map[desig_clean] = node

            base = node.get("base_number")
            det_from_desig = None
            if base is None:
                dets = self.detect_designations(desig)
                if dets:
                    det_from_desig = dets[0]
                    base = det_from_desig.get("base_number")
            if base is None:
                continue
            try:
                base_int = int(base)
            except (ValueError, TypeError):
                continue

            part = str(node.get("part")) if node.get("part") is not None else (det_from_desig.get("part") if det_from_desig else None)
            sec = str(node.get("section")) if node.get("section") is not None else (det_from_desig.get("section") if det_from_desig else None)
            if not node.get("year") and det_from_desig and det_from_desig.get("year"):
                try:
                    node["year"] = int(det_from_desig["year"])
                except (ValueError, TypeError):
                    pass

            # Add to family_parts
            part_dict = self.family_parts.setdefault(base_int, {})
            part_dict.setdefault(part, []).append(node)

            # Add to family_sections
            sec_dict = self.family_sections.setdefault((base_int, part), {})
            sec_dict.setdefault(sec, []).append(node)

        # Sort all edition candidate lists by year descending
        def _get_year(n):
            try:
                return int(n.get("year") or 0)
            except (ValueError, TypeError):
                return 0

        for base_int, part_dict in self.family_parts.items():
            for p, n_list in part_dict.items():
                n_list.sort(key=_get_year, reverse=True)

        for (base_int, part), sec_dict in self.family_sections.items():
            for s, n_list in sec_dict.items():
                n_list.sort(key=_get_year, reverse=True)

    def detect_designations(self, text: str) -> List[Dict[str, Any]]:
        """
        Scan text for all BIS designation occurrences.
        Returns list of structured matches with offsets and canonical form.
        """
        matches = []
        for m in DESIGNATION_REGEX.finditer(text):
            raw_match = m.group(0).strip()
            base_str = m.group(1)
            part_str = m.group(2)
            sec_str = m.group(3)
            year_str = m.group(4)

            try:
                base_num = int(base_str)
            except ValueError:
                continue

            # Build canonical designation string
            prefix = "IS"
            if "iec" in raw_match.lower():
                prefix = "IS/IEC"
            elif "iso" in raw_match.lower():
                prefix = "IS/ISO"

            if part_str and sec_str:
                canonical = f"{prefix} {base_num} (Part {part_str}/Sec {sec_str})"
            elif part_str:
                canonical = f"{prefix} {base_num} (Part {part_str})"
            else:
                canonical = f"{prefix} {base_num}"

            if year_str:
                canonical_with_year = f"{canonical}:{year_str}"
            else:
                canonical_with_year = canonical

            matches.append({
                "raw_match": raw_match,
                "start_char": m.start(),
                "end_char": m.end(),
                "prefix": prefix,
                "base_number": base_num,
                "part": part_str,
                "section": sec_str,
                "year": year_str,
                "canonical_base": canonical,
                "canonical_designation": canonical_with_year,
            })

        return matches

    def is_multi_part_family(self, base_number: int) -> bool:
        """True if the family has more than one part or has parts defined."""
        if base_number not in self.family_parts:
            return False
        parts = self.family_parts[base_number]
        # Has explicit parts other than None
        non_none_parts = [p for p in parts.keys() if p is not None]
        return len(non_none_parts) > 0

    def resolve_candidate(self, detected: Dict[str, Any]) -> Optional[dict]:
        """
        Resolve detected designation to a candidate graph node following strict hierarchy:
        1. Exact canonical designation match (with year if provided).
        2. Exact Part / Section edition resolution.
        3. Part-specified query without year -> latest active edition for that part.
        4. Umbrella base query (e.g. 'IS 7098' with no part) -> Do NOT silently select a part!
           Returns None to force part disambiguation / avoid false precision.
        5. Single-part standard (e.g. 'IS 4984') -> latest active edition.
        """
        desig_full = detected.get("canonical_designation", "").strip().upper()
        base_int = detected.get("base_number")
        part = detected.get("part")
        sec = detected.get("section")
        req_year = detected.get("year")

        # MULTI-PART FAMILY SAFETY RULE:
        # If the standard family is multi-part (e.g. IS 7098 has Part 1, Part 2),
        # a bare query like "IS 7098" (part is None) must NEVER silently select a part
        # or resolve to an unhydrated stub reference.
        if base_int is not None and self.is_multi_part_family(base_int) and part is None:
            # If a specific year was requested (e.g. IS 7098:2011), check if an exact base edition matches that year
            if req_year:
                part_dict = self.family_parts.get(base_int, {})
                all_matching = []
                for p, ed_list in part_dict.items():
                    for ed in ed_list:
                        if str(ed.get("year")) == str(req_year):
                            all_matching.append(ed)
                if len(all_matching) == 1:
                    return all_matching[0]
            # Bare multi-part umbrella query fails closed
            return None

        if desig_full in self.exact_map:
            # Only return exact map if it's not an unhydrated stub for a multi-part family
            node = self.exact_map[desig_full]
            if not (node.get("candidate_status") == "SUPPORTING_ONLY" and self.is_multi_part_family(base_int)):
                return node

        if base_int is None or base_int not in self.family_parts:
            return None

        part_dict = self.family_parts[base_int]

        # Case 1: Specific part requested (e.g. IS 7098 Part 2)
        if part is not None:
            if part not in part_dict:
                return None
            candidate_editions = part_dict[part]

            # If section requested, filter by section
            if sec is not None:
                sec_dict = self.family_sections.get((base_int, part), {})
                candidate_editions = sec_dict.get(sec, [])

            if not candidate_editions:
                return None

            # If exact year requested, match year
            if req_year:
                for c in candidate_editions:
                    if str(c.get("year")) == str(req_year):
                        return c
                # If specific requested year not found in KB, return None (fail closed)
                return None

            # Return latest active edition for this part
            # Attach candidate_editions to node copy so lifecycle gate can audit all editions
            best_cand = dict(candidate_editions[0])
            best_cand["candidate_editions"] = [c.get("designation") for c in candidate_editions]
            return best_cand

        # Case 2: Bare base query (part is None, e.g. "IS 7098" or "IS 4984")
        if self.is_multi_part_family(base_int):
            # MULTI-PART FAMILY SAFETY RULE:
            # Query like "IS 7098" does not specify Part 1 or Part 2.
            # Do NOT silently choose a part!
            # If a year was specified (e.g. IS 7098:2011), check if an exact base or unique part matches that year
            if req_year:
                all_matching = []
                for p, ed_list in part_dict.items():
                    for ed in ed_list:
                        if str(ed.get("year")) == str(req_year):
                            all_matching.append(ed)
                if len(all_matching) == 1:
                    return all_matching[0]
            # Otherwise, umbrella query cannot resolve to a single part safely
            return None

        # Case 3: Single-part standard family (e.g. IS 4984)
        base_editions = part_dict.get(None, [])
        if not base_editions:
            # Check if all editions under any key
            base_editions = [n for ed_list in part_dict.values() for n in ed_list]

        if not base_editions:
            return None

        if req_year:
            for c in base_editions:
                if str(c.get("year")) == str(req_year):
                    return c
            return None

        best_cand = dict(base_editions[0])
        best_cand["candidate_editions"] = [c.get("designation") for c in base_editions]
        return best_cand
