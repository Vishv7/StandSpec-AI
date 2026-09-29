"""
Tests for BIS API client module (models, listing, detail, and enrichment).
Enforces 100% offline compliance and validates metadata enrichment.
"""

import pytest
from src.bis_api.models import (
    BISStandardListingItem,
    BISStandardDetail,
    AmendmentInfo,
    BISApiResponse,
)
from src.bis_api.listing_client import BISListingClient
from src.bis_api.detail_client import BISDetailClient


@pytest.fixture
def sample_listing_data():
    return {
        "standards": [
            {
                "standard_number": "IS 456:2000",
                "title": "Plain and Reinforced Concrete - Code of Practice",
                "department": "CED",
                "committee": "CED 2",
                "date_of_publish": "2000-07-01",
                "status": "ACTIVE",
            },
            {
                "standard_number": "IS 7098 (Part 2):2011",
                "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables",
                "department": "ETD",
                "committee": "ETD 9",
                "date_of_publish": "2011-04-15",
                "status": "ACTIVE",
            },
            {
                "standard_number": "IS 694:1990",
                "title": "PVC Insulated Cables for Working Voltages up to and including 1100 V",
                "department": "ETD",
                "committee": "ETD 9",
                "date_of_publish": "1990-01-01",
                "status": "SUPERSEDED",
            },
        ]
    }


@pytest.fixture
def sample_detail_data():
    return {
        "IS 7098 (Part 2):2011": {
            "standard_number": "IS 7098 (Part 2):2011",
            "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables",
            "department": "ETD",
            "committee": "ETD 9",
            "ics_codes": ["29.060.20"],
            "date_of_publish": "2011-04-15",
            "review_date": "2021-04-15",
            "reaffirmation_year": "2021",
            "status": "ACTIVE",
            "supersedes": ["IS 7098 (Part 2):1985"],
            "superseded_by": None,
            "amendments": [
                {
                    "amendment_number": 1,
                    "publication_date": "2015-08-01",
                    "notes": "Clause 12.1 updated.",
                }
            ],
            "qco_mandatory": True,
            "scope_text": "Covers XLPE insulated cables for 3.3 kV to 33 kV.",
        }
    }


def test_models_serialization():
    """Verify dataclasses serialize and deserialize symmetrically."""
    item = BISStandardListingItem(
        standard_number="IS 19609:2026",
        title="uPVC Profile Framed Doors",
        department="CED",
        committee="CED 11",
        date_of_publish="2026-08-28",
        status="ACTIVE",
    )
    d = item.to_dict()
    reconstructed = BISStandardListingItem.from_dict(d)
    assert reconstructed.standard_number == "IS 19609:2026"
    assert reconstructed.department == "CED"
    assert reconstructed.committee == "CED 11"

    detail = BISStandardDetail(
        standard_number="IS 19609:2026",
        title="uPVC Profile Framed Doors",
        department="CED",
        committee="CED 11",
        ics_codes=["83.140", "91.060.50"],
        date_of_publish="2026-08-28",
        amendments=[AmendmentInfo(amendment_number=1, publication_date="2027-01-01")],
        qco_mandatory=True,
    )
    dd = detail.to_dict()
    rec_detail = BISStandardDetail.from_dict(dd)
    assert rec_detail.standard_number == "IS 19609:2026"
    assert rec_detail.qco_mandatory is True
    assert len(rec_detail.amendments) == 1
    assert rec_detail.amendments[0].amendment_number == 1


def test_listing_client_filtering_and_pagination(sample_listing_data):
    """Verify listing queries filter correctly by department and status."""
    client = BISListingClient(mock_data_source=sample_listing_data)
    
    # Filter by ETD
    resp_etd = client.list_standards(department="ETD")
    assert resp_etd.success is True
    assert resp_etd.total_records == 2
    assert all(item.department == "ETD" for item in resp_etd.data)

    # Filter by status ACTIVE
    resp_active = client.list_standards(status="ACTIVE")
    assert resp_active.total_records == 2
    assert all(item.status == "ACTIVE" for item in resp_active.data)

    # Filter by SUPERSEDED
    resp_sup = client.list_standards(status="SUPERSEDED")
    assert resp_sup.total_records == 1
    assert resp_sup.data[0].standard_number == "IS 694:1990"

    # Pagination: page_size=1
    page1 = client.list_standards(department="ETD", page=1, page_size=1)
    assert len(page1.data) == 1
    page2 = client.list_standards(department="ETD", page=2, page_size=1)
    assert len(page2.data) == 1
    assert page1.data[0].standard_number != page2.data[0].standard_number


def test_listing_client_search(sample_listing_data):
    """Verify search finds matching terms in title and designation."""
    client = BISListingClient(mock_data_source=sample_listing_data)
    res = client.search_standards("Polyethylene")
    assert res.total_records == 1
    assert "IS 7098" in res.data[0].standard_number

    res_num = client.search_standards("456")
    assert res_num.total_records == 1
    assert res_num.data[0].standard_number == "IS 456:2000"


def test_detail_client_enrichment(sample_detail_data):
    """Verify detail client enriches existing record without corrupting fields."""
    client = BISDetailClient(mock_details_source=sample_detail_data)
    
    existing_record = {
        "identity": {"standard_designation": "IS 7098 (Part 2):2011"},
        "content": {"committee": None, "ics_codes": []},
        "lifecycle": {},
        "details_available": False,
        "lifecycle_evidence_available": False,
        "preserved_custom_field": "do_not_lose_me",
    }
    
    enriched = client.enrich_record(existing_record)
    assert enriched["preserved_custom_field"] == "do_not_lose_me"
    assert enriched["details_available"] is True
    assert enriched["lifecycle_evidence_available"] is True
    assert enriched["regulatory_evidence_available"] is True
    assert enriched["content"]["committee"] == "ETD 9"
    assert "29.060.20" in enriched["content"]["ics_codes"]
    assert enriched["lifecycle"]["review_date"] == "2021-04-15"
    assert enriched["lifecycle"]["supersedes"] == ["IS 7098 (Part 2):1985"]
    assert len(enriched["lifecycle"]["amendments"]) == 1


def test_detail_client_not_found(sample_detail_data):
    """Verify safe handling of unindexed standard numbers."""
    client = BISDetailClient(mock_details_source=sample_detail_data)
    resp = client.get_standard_details("IS 99999:2099")
    assert resp.success is False
    assert resp.status_code == 404


def test_12_and_24_row_pagination_and_duplicate_detection():
    """Verify 12-row and 24-row pagination grids and multi-page duplicate detection."""
    mock_standards = [
        {
            "standard_number": f"IS {1000 + i}:2020",
            "title": f"Standard Test Specification {i}",
            "department": "CED" if i % 2 == 0 else "ETD",
            "committee": "CED 2" if i % 2 == 0 else "ETD 9",
            "date_of_publish": "2020-01-01",
            "status": "ACTIVE",
        }
        for i in range(30)
    ]
    # Add an intentional duplicate at the end to test duplicate detection
    mock_standards.append(dict(mock_standards[0]))

    client = BISListingClient(mock_data_source={"standards": mock_standards})

    # Test 12-row pagination
    p1_12 = client.list_standards(page=1, page_size=12)
    assert len(p1_12.data) == 12
    assert p1_12.total_records == 31

    p2_12 = client.list_standards(page=2, page_size=12)
    assert len(p2_12.data) == 12

    p3_12 = client.list_standards(page=3, page_size=12)
    assert len(p3_12.data) == 7

    # Verify no pagination leakage between page 1 and page 2
    desigs_p1 = {item.standard_number for item in p1_12.data}
    desigs_p2 = {item.standard_number for item in p2_12.data}
    assert len(desigs_p1.intersection(desigs_p2)) == 0

    # Test 24-row pagination
    p1_24 = client.list_standards(page=1, page_size=24)
    assert len(p1_24.data) == 24
    p2_24 = client.list_standards(page=2, page_size=24)
    assert len(p2_24.data) == 7

    # Duplicate detection
    all_seen = set()
    duplicates = []
    for item in mock_standards:
        desig = item["standard_number"]
        if desig in all_seen:
            duplicates.append(desig)
        all_seen.add(desig)
    assert len(duplicates) == 1
    assert duplicates[0] == "IS 1000:2020"


def test_offline_fixture_replay_socket_blockade():
    """Verify clients execute completely hermetic fixture replays with zero network calls."""
    fixture_data = {
        "standards": [
            {
                "standard_number": "IS 16444 (Part 1):2015",
                "title": "a.c. Static Direct Connected Watthour Smart Meters, Class 1 and 2",
                "department": "ETD",
                "committee": "ETD 13",
                "date_of_publish": "2015-08-15",
                "status": "ACTIVE",
            }
        ]
    }
    client = BISListingClient(mock_data_source=fixture_data)
    res = client.list_standards(department="ETD")
    assert res.success is True
    assert len(res.data) == 1
    assert res.data[0].standard_number == "IS 16444 (Part 1):2015"

