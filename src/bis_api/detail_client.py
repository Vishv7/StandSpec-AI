"""
Client for retrieving detailed metadata, lifecycle status, committee,
and supersession history for individual standards from BIS API.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.bis_api.models import BISStandardDetail, BISApiResponse

logger = logging.getLogger(__name__)


class BISDetailClient:
    """
    Client for retrieving detailed standard information from BIS.
    Supports record enrichment and offline mock playback.
    """

    def __init__(
        self,
        base_url: str = "https://standardsbis.bsbedge.com/api",
        mock_details_source: Optional[Dict[str, Dict[str, Any]]] = None,
        cache_dir: Optional[str | Path] = None,
        timeout: int = 15,
    ):
        self.base_url = base_url.rstrip("/")
        self.mock_details_source = mock_details_source or {}
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.timeout = timeout

    def get_standard_details(self, standard_number: str) -> BISApiResponse:
        """
        Fetch detailed metadata for a standard designation.
        """
        norm_key = standard_number.strip().upper()
        if self.mock_details_source:
            # Case-insensitive lookup
            for key, val in self.mock_details_source.items():
                if key.strip().upper() == norm_key:
                    detail = BISStandardDetail.from_dict(val)
                    return BISApiResponse(
                        success=True,
                        status_code=200,
                        data=detail,
                        total_records=1,
                    )
            return BISApiResponse(
                success=False,
                status_code=404,
                error_message=f"Standard '{standard_number}' not found in mock details source.",
            )

        return BISApiResponse(
            success=False,
            status_code=404,
            error_message="Offline mode active: provide mock_details_source for offline replay.",
        )

    def enrich_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich an existing V1.2 JSONL record with authoritative detail metadata.
        Sets details_available and lifecycle_evidence_available appropriately.
        Preserves all existing record fields.
        """
        enriched = dict(record)
        raw_desig = (
            record.get("identity", {}).get("standard_designation")
            or record.get("input", {}).get("raw_standard_number")
            or record.get("is_number", "")
        )
        if not raw_desig:
            return enriched

        resp = self.get_standard_details(raw_desig)
        if resp.success and isinstance(resp.data, BISStandardDetail):
            detail: BISStandardDetail = resp.data
            
            # Enrich content block if present
            if "content" in enriched and isinstance(enriched["content"], dict):
                content = dict(enriched["content"])
                if detail.committee and not content.get("committee"):
                    content["committee"] = detail.committee
                if detail.ics_codes and not content.get("ics_codes"):
                    content["ics_codes"] = detail.ics_codes
                enriched["content"] = content

            # Enrich lifecycle block
            if "lifecycle" not in enriched:
                enriched["lifecycle"] = {}
            
            lifecycle = dict(enriched.get("lifecycle", {}))
            if detail.date_of_publish:
                lifecycle["date_of_publish"] = detail.date_of_publish
            if detail.review_date:
                lifecycle["review_date"] = detail.review_date
            if detail.reaffirmation_year:
                lifecycle["reaffirmation_year"] = detail.reaffirmation_year
            if detail.status:
                lifecycle["status"] = detail.status
            if detail.supersedes:
                lifecycle["supersedes"] = detail.supersedes
            if detail.superseded_by:
                lifecycle["superseded_by"] = detail.superseded_by
            if detail.amendments:
                lifecycle["amendments"] = [
                    {
                        "amendment_number": a.amendment_number,
                        "publication_date": a.publication_date,
                        "notes": a.notes,
                    }
                    for a in detail.amendments
                ]
            enriched["lifecycle"] = lifecycle

            # Update evidence flags
            enriched["details_available"] = True
            enriched["lifecycle_evidence_available"] = True
            if detail.qco_mandatory:
                enriched["regulatory_evidence_available"] = True

        return enriched
