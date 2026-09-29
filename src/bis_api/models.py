"""
Data models for BIS API integration.
Defines strongly-typed schemas for listing items, standard details,
and API response envelopes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class BISStandardListingItem:
    """Represents a single standard summary entry from a catalogue listing query."""
    standard_number: str
    title: str
    department: str
    committee: Optional[str] = None
    date_of_publish: Optional[str] = None
    status: str = "ACTIVE"  # ACTIVE, SUPERSEDED, WITHDRAWN
    type_of_standard: Optional[str] = None
    degree_of_equivalence: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standard_number": self.standard_number,
            "title": self.title,
            "department": self.department,
            "committee": self.committee,
            "date_of_publish": self.date_of_publish,
            "status": self.status,
            "type_of_standard": self.type_of_standard,
            "degree_of_equivalence": self.degree_of_equivalence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BISStandardListingItem:
        return cls(
            standard_number=data.get("standard_number", ""),
            title=data.get("title", ""),
            department=data.get("department", ""),
            committee=data.get("committee"),
            date_of_publish=data.get("date_of_publish"),
            status=data.get("status", "ACTIVE"),
            type_of_standard=data.get("type_of_standard"),
            degree_of_equivalence=data.get("degree_of_equivalence"),
        )


@dataclass
class AmendmentInfo:
    """Represents an amendment to an Indian Standard."""
    amendment_number: int
    publication_date: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class BISStandardDetail:
    """Detailed record for an individual Indian Standard from BIS API."""
    standard_number: str
    title: str
    department: str
    committee: Optional[str] = None
    ics_codes: List[str] = field(default_factory=list)
    date_of_publish: Optional[str] = None
    review_date: Optional[str] = None
    reaffirmation_year: Optional[str] = None
    status: str = "ACTIVE"  # ACTIVE, SUPERSEDED, WITHDRAWN
    supersedes: List[str] = field(default_factory=list)
    superseded_by: Optional[str] = None
    amendments: List[AmendmentInfo] = field(default_factory=list)
    qco_mandatory: bool = False
    scope_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standard_number": self.standard_number,
            "title": self.title,
            "department": self.department,
            "committee": self.committee,
            "ics_codes": self.ics_codes,
            "date_of_publish": self.date_of_publish,
            "review_date": self.review_date,
            "reaffirmation_year": self.reaffirmation_year,
            "status": self.status,
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
            "amendments": [
                {
                    "amendment_number": a.amendment_number,
                    "publication_date": a.publication_date,
                    "notes": a.notes,
                }
                for a in self.amendments
            ],
            "qco_mandatory": self.qco_mandatory,
            "scope_text": self.scope_text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BISStandardDetail:
        amendments = [
            AmendmentInfo(
                amendment_number=a.get("amendment_number", 1),
                publication_date=a.get("publication_date"),
                notes=a.get("notes"),
            )
            for a in data.get("amendments", [])
        ]
        return cls(
            standard_number=data.get("standard_number", ""),
            title=data.get("title", ""),
            department=data.get("department", ""),
            committee=data.get("committee"),
            ics_codes=data.get("ics_codes", []),
            date_of_publish=data.get("date_of_publish"),
            review_date=data.get("review_date"),
            reaffirmation_year=data.get("reaffirmation_year"),
            status=data.get("status", "ACTIVE"),
            supersedes=data.get("supersedes", []),
            superseded_by=data.get("superseded_by"),
            amendments=amendments,
            qco_mandatory=data.get("qco_mandatory", False),
            scope_text=data.get("scope_text"),
        )


@dataclass
class BISApiResponse:
    """Generic API response envelope."""
    success: bool
    status_code: int
    data: Any = None
    total_records: int = 0
    page: int = 1
    page_size: int = 50
    error_message: Optional[str] = None
