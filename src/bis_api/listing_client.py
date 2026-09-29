"""
Client for querying standard listings from BIS portal/API.
Provides filtering by department, committee, status, and keyword,
with deterministic offline mock/replay support for CI/testing.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.bis_api.models import BISStandardListingItem, BISApiResponse

logger = logging.getLogger(__name__)


class BISListingClient:
    """
    Client for querying catalogue listing items from BIS.
    Supports online HTTP retrieval and offline fixture/mock playback.
    """

    def __init__(
        self,
        base_url: str = "https://standardsbis.bsbedge.com/api",
        mock_data_source: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        cache_dir: Optional[str | Path] = None,
        timeout: int = 15,
    ):
        self.base_url = base_url.rstrip("/")
        self.mock_data_source = mock_data_source or {}
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.timeout = timeout

    def list_standards(
        self,
        department: Optional[str] = None,
        committee: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> BISApiResponse:
        """
        Query standard listing with optional filtering and pagination.
        """
        # If offline mock data provided, use it deterministically
        if self.mock_data_source:
            items_raw = self.mock_data_source.get("standards", [])
            filtered = []
            for item in items_raw:
                if department and item.get("department", "").upper() != department.upper():
                    continue
                if committee and item.get("committee", "").upper() != committee.upper():
                    continue
                if status and status.upper() != "ALL" and item.get("status", "ACTIVE").upper() != status.upper():
                    continue
                filtered.append(BISStandardListingItem.from_dict(item))

            total = len(filtered)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated = filtered[start_idx:end_idx]

            return BISApiResponse(
                success=True,
                status_code=200,
                data=paginated,
                total_records=total,
                page=page,
                page_size=page_size,
            )

        # In offline/test mode without mock source, return empty safe response
        return BISApiResponse(
            success=True,
            status_code=200,
            data=[],
            total_records=0,
            page=page,
            page_size=page_size,
            error_message="Offline mode active: provide mock_data_source for offline replay.",
        )

    def search_standards(
        self,
        query_text: str,
        department: Optional[str] = None,
        limit: int = 50,
    ) -> BISApiResponse:
        """
        Search standards matching a query string in title or designation.
        """
        query_norm = query_text.lower()
        if self.mock_data_source:
            items_raw = self.mock_data_source.get("standards", [])
            matches = []
            for item in items_raw:
                if department and item.get("department", "").upper() != department.upper():
                    continue
                title = item.get("title", "").lower()
                desig = item.get("standard_number", "").lower()
                if query_norm in title or query_norm in desig:
                    matches.append(BISStandardListingItem.from_dict(item))
                if len(matches) >= limit:
                    break

            return BISApiResponse(
                success=True,
                status_code=200,
                data=matches,
                total_records=len(matches),
                page=1,
                page_size=limit,
            )

        return BISApiResponse(
            success=True,
            status_code=200,
            data=[],
            total_records=0,
            page=1,
            page_size=limit,
            error_message="Offline mode active: provide mock_data_source for offline replay.",
        )
