"""
Tests for StandSpec AI FastAPI Gateway Endpoints.
Verifies all REST endpoints and PDF processing.
"""

import io
from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "READY"
    assert data["indexed_standards"] > 5000
    assert "CED" in data["supported_departments"]
    assert "ETD" in data["supported_departments"]


def test_query_recommend_pipeline():
    payload = {
        "query": "Supply of 1.1 kV grade XLPE insulated 3-core 240 sq mm aluminium conductor underground cables",
        "mode": "pipeline",
        "evaluation_date": "2026-09-30",
    }
    res = client.post("/api/v1/query/recommend", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "decision_state" in data
    assert data["decision_state"] in [
        "PRIMARY_RECOMMENDATION_AVAILABLE",
        "EXPERT_REVIEW_REQUIRED",
        "CONDITIONAL_RECOMMENDATION",
    ]


def test_query_extract():
    payload = {
        "query": "Supply of 1.1 kV grade XLPE insulated 3-core 240 sq mm aluminium conductor underground cables"
    }
    res = client.post("/api/v1/query/extract", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "requirements" in data
    reqs = data["requirements"]
    assert "product" in reqs
    assert "voltage" in reqs


def test_standards_search():
    res = client.get("/api/v1/standards/search?q=7098")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] > 0
    assert any("7098" in s["designation"] for s in data["standards"])


def test_standard_details():
    res = client.get("/api/v1/standards/IS 7098 (Part 1):1988")
    assert res.status_code == 200
    data = res.json()
    assert data["designation"] == "IS 7098 (Part 1):1988"
    assert "lifecycle" in data
    assert "regulatory" in data


def test_tender_pdf_upload_mock():
    # Create an in-memory PDF with pypdf
    import pypdf
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    # Using simple pdf bytes
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    response = client.post(
        "/api/v1/tender/upload",
        files={"file": ("tender_test.pdf", pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "tender_test.pdf"
    assert "clauses" in data
    assert "extraction_metadata" in data
    assert data["extraction_metadata"]["extraction_method"] == "pypdf_text_extraction"
    assert data["tender_metadata"]["publish_date_state"] in ("VERIFIED_EXTRACTED", "NOT_VERIFIED")


def test_tender_pdf_invalid_signature():
    """Verify PDF upload rejects files without '%PDF-' file signature."""
    fake_bytes = b"NOT_A_REAL_PDF_FILE"
    response = client.post(
        "/api/v1/tender/upload",
        files={"file": ("malicious.pdf", fake_bytes, "application/pdf")}
    )
    assert response.status_code == 400
    err = response.json()
    assert "error_code" in err
    assert "Missing '%PDF-'" in err["message"]
    assert "request_id" in err


def test_tender_pdf_invalid_extension():
    """Verify PDF upload rejects non-PDF file extensions."""
    response = client.post(
        "/api/v1/tender/upload",
        files={"file": ("tender.docx", b"%PDF-dummy", "application/pdf")}
    )
    assert response.status_code == 400
    err = response.json()
    assert "error_code" in err
    assert "Only PDF files are supported" in err["message"]


def test_api_error_sanitization():
    """Verify 404 or invalid route returns structured sanitized error."""
    response = client.get("/api/v1/non_existent_route")
    assert response.status_code == 404
    err = response.json()
    assert err["error_code"] == "HTTP_404"
    assert "request_id" in err

