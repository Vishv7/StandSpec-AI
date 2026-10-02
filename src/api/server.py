"""
StandSpec AI — FastAPI REST & WebSocket Server Gateway
Provides production API endpoints connecting the React frontend to the
StandSpecAgent, StandSpecRecommendationEngine, and TenderPDFExtractor.
"""

import os
import sys
import json
import time
import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from fastapi import FastAPI, File, UploadFile, Query, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.agent.agent import StandSpecAgent
from src.recommendation.engine import StandSpecRecommendationEngine
from src.api.pdf_extractor import TenderPDFExtractor
from src.version import ENGINE_VERSION, RELEASE_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StandSpecAPI")

app = FastAPI(
    title="StandSpec AI Gateway",
    description="Automated Indian Standards (BIS) Procurement Recommendation & Statutory QCO Compliance Engine",
    version=ENGINE_VERSION,
)

# Enable CORS — configurable via environment for security (PS 26108 P1)
_cors_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
_allow_credentials = False if "*" in _cors_origins else True
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    req_id = str(uuid.uuid4())[:8]
    error_code = f"HTTP_{exc.status_code}"
    detail = exc.detail if isinstance(exc.detail, str) else "HTTP request failed."
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": error_code,
            "message": detail,
            "request_id": req_id,
        },
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    req_id = str(uuid.uuid4())[:8]
    logger.exception(f"Unhandled server error [request_id={req_id}]")
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": f"An internal server error occurred. Reference: {req_id}",
            "request_id": req_id,
        },
    )

# Global singleton engine and agent references
_engine: Optional[StandSpecRecommendationEngine] = None
_agent: Optional[StandSpecAgent] = None
_pdf_extractor: Optional[TenderPDFExtractor] = None


def get_engine() -> StandSpecRecommendationEngine:
    global _engine
    if _engine is None:
        logger.info("Initializing StandSpecRecommendationEngine from release...")
        _engine = StandSpecRecommendationEngine.from_release()
    return _engine


def get_agent() -> StandSpecAgent:
    global _agent
    if _agent is None:
        logger.info("Initializing StandSpecAgent from release...")
        _agent = StandSpecAgent.from_release()
    return _agent


def get_pdf_extractor() -> TenderPDFExtractor:
    global _pdf_extractor
    if _pdf_extractor is None:
        eng = get_engine()
        _pdf_extractor = TenderPDFExtractor(extractor=eng.extractor)
    return _pdf_extractor


# ── Request / Response Models ──

class QueryRecommendRequest(BaseModel):
    query: str = Field(..., description="Procurement requirement text or tender line item", min_length=2)
    mode: str = Field("auto", description="Execution mode: 'auto', 'pipeline', 'llm'")
    evaluation_date: Optional[str] = Field(None, description="Evaluation date in YYYY-MM-DD format")
    top_k: int = Field(5, description="Number of candidate standards to return")


class ExtractOnlyRequest(BaseModel):
    query: str = Field(..., description="Raw procurement text to extract entities from", min_length=2)


class BatchRecommendRequest(BaseModel):
    items: List[Dict[str, Any]] = Field(..., description="List of tender items with raw_text and item_id")
    evaluation_date: Optional[str] = Field(None, description="Evaluation date in YYYY-MM-DD format")


# ── REST Endpoints ──

@app.get("/api/v1/health")
def health():
    """Returns engine operational status and release metadata."""
    eng = get_engine()
    node_count = len(eng.standards_graph.get("nodes", []))
    qco_count = len(eng.regulatory_gate.designation_to_qco)
    return {
        "status": "READY",
        "engine_version": ENGINE_VERSION,
        "release_id": RELEASE_ID,
        "indexed_standards": node_count,
        "mandatory_qco_records": qco_count,
        "default_evaluation_date": eng.default_evaluation_date,
        "supported_departments": ["CED", "ETD"],
    }


@app.post("/api/v1/query/recommend")
def recommend_query(payload: QueryRecommendRequest):
    """
    Executes full recommendation pipeline.
    Uses StandSpecAgent (with deterministic safety validator) or deterministic pipeline.
    """
    start_time = time.time()
    try:
        if payload.mode in ("auto", "llm"):
            agent = get_agent()
            res = agent.answer(
                query=payload.query,
                mode=payload.mode,
                evaluation_date=payload.evaluation_date,
            )
            # Ensure query text is preserved in response
            if "query" not in res:
                res["query"] = {
                    "raw_text": payload.query,
                    "language": (res.get("normalized_requirements") or {}).get("language", "en"),
                }
            latency_ms = int((time.time() - start_time) * 1000)
            if "agent_metadata" in res and res["agent_metadata"]:
                res["agent_metadata"]["latency_ms"] = latency_ms
            return res
        else:
            # Deterministic Pipeline only
            eng = get_engine()
            res = eng.recommend(
                raw_text=payload.query,
                evaluation_date=payload.evaluation_date,
                top_k=payload.top_k,
            )
            res["agent_metadata"] = {
                "execution_mode": "deterministic_pipeline",
                "step_count": 9,
                "latency_ms": int((time.time() - start_time) * 1000),
                "validator_status": "DETERMINISTIC_PASS",
            }
            return res
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        logger.exception(f"Error processing recommendation query [request_id={request_id}]")
        raise HTTPException(status_code=500, detail=f"Recommendation service could not complete the request. Reference: {request_id}")


@app.post("/api/v1/query/extract")
def extract_entities(payload: ExtractOnlyRequest):
    """Directly extracts structured, grounded technical requirements with character spans."""
    try:
        eng = get_engine()
        return eng.extractor.extract(payload.query)
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        logger.exception(f"Error extracting entities [request_id={request_id}]")
        raise HTTPException(status_code=500, detail=f"Entity extraction could not complete the request. Reference: {request_id}")


@app.post("/api/v1/tender/upload")
async def upload_tender_pdf(
    file: UploadFile = File(...),
    evaluation_date: Optional[str] = Query(None),
    auto_verify: bool = Query(False, description="Whether to automatically run recommendation on all technical clauses immediately"),
):
    """
    Accepts PDF tender document, extracts text, identifies metadata,
    and segments clauses into classified items (Technical Procurement vs Administrative).
    If auto_verify is False (recommended), clauses are returned for user review & selection.
    """
    filename = file.filename or "tender.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported (.pdf extension required).")

    if file.content_type and file.content_type.lower() not in (
        "application/pdf",
        "application/x-pdf",
        "application/octet-stream",
    ):
        raise HTTPException(status_code=400, detail=f"Invalid MIME type '{file.content_type}'. Must be application/pdf.")

    # PDF size and page limits (PS 26108 P1)
    MAX_PDF_SIZE_MB = int(os.environ.get("MAX_PDF_SIZE_MB", "20"))
    MAX_PDF_PAGES = int(os.environ.get("MAX_PDF_PAGES", "200"))

    try:
        pdf_bytes = await file.read()
        if not pdf_bytes.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="Invalid PDF file: Missing '%PDF-' file signature.")

        pdf_size_mb = len(pdf_bytes) / (1024 * 1024)
        if pdf_size_mb > MAX_PDF_SIZE_MB:
            raise HTTPException(
                status_code=413,
                detail=f"PDF file exceeds maximum allowed size of {MAX_PDF_SIZE_MB} MB ({pdf_size_mb:.1f} MB uploaded)."
            )
        try:
            extractor = get_pdf_extractor()
            doc = extractor.extract_from_bytes(pdf_bytes, filename=filename)
        except HTTPException:
            raise
        except Exception as pe:
            logger.warning(f"Failed to parse PDF bytes: {pe}")
            raise HTTPException(
                status_code=400,
                detail=f"Malformed, encrypted, or corrupted PDF document: {str(pe)[:120]}"
            )
        page_count = doc.get("page_count", 0)
        if page_count > MAX_PDF_PAGES:
            raise HTTPException(
                status_code=413,
                detail=f"PDF has {page_count} pages, exceeding maximum of {MAX_PDF_PAGES} pages."
            )

        if auto_verify:
            eng = get_engine()
            eval_date = evaluation_date or eng.default_evaluation_date

            for cl in doc.get("clauses", []):
                if not cl.get("is_technical", True):
                    cl["status"] = "EXCLUDED_ADMINISTRATIVE"
                    continue
                try:
                    rec = eng.recommend(raw_text=cl["raw_text"], evaluation_date=eval_date, top_k=3)
                    # Section 27: Each technical clause retains complete backend recommendation result
                    cl["analysis"] = rec
                    cl["decision_state"] = rec.get("decision_state", "UNKNOWN")
                    primary = rec.get("primary_recommendation")
                    review = rec.get("review_candidate")
                    cl["primary_recommendation"] = primary
                    cl["review_candidate"] = review

                    # Section 28: Citation lifecycle check
                    cited_std = cl.get("cited_standard")
                    if cited_std:
                        cl["citation_lifecycle_check"] = eng.lifecycle_gate.check_citation_lifecycle(cited_std, eval_date)

                    if primary:
                        cl["status"] = "RECOMMENDATION_AVAILABLE"
                    elif review:
                        cl["status"] = "EXPERT_REVIEW_REQUIRED"
                    else:
                        cl["status"] = "UNRESOLVED"
                except Exception:
                    logger.exception(f"Error processing clause {cl.get('item_id')}")
                    cl["status"] = "UNPROCESSED"

        return doc
    except HTTPException:
        raise
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        logger.exception(f"Error parsing PDF tender [request_id={request_id}]")
        raise HTTPException(status_code=500, detail=f"Failed to process tender document. Reference: {request_id}")


@app.post("/api/v1/tender/batch-recommend")
def batch_recommend(payload: BatchRecommendRequest):
    """Runs recommendation pipeline across multiple selected tender clauses."""
    eng = get_engine()
    results = []
    eval_date = payload.evaluation_date or eng.default_evaluation_date

    for item in payload.items:
        raw_text = item.get("raw_text") or item.get("text") or ""
        item_id = item.get("item_id")
        if not raw_text:
            continue
        try:
            rec = eng.recommend(raw_text=raw_text, evaluation_date=eval_date, top_k=3)
            rec["item_id"] = item_id
            cited_std = item.get("cited_standard")
            if cited_std:
                rec["citation_lifecycle_check"] = eng.lifecycle_gate.check_citation_lifecycle(cited_std, eval_date)
            results.append(rec)
        except Exception as e:
            request_id = str(uuid.uuid4())[:8]
            logger.exception(f"Error in batch recommendation for item {item_id} [request_id={request_id}]")
            results.append({
                "item_id": item_id,
                "error": f"Recommendation could not be completed. Reference: {request_id}",
                "decision_state": "ERROR",
            })

    return {"count": len(results), "results": results}


@app.get("/api/v1/standards/search")
def search_standards(
    q: str = Query(..., min_length=2),
    department: Optional[str] = Query(None),
    top_k: int = Query(20),
):
    """Searches indexed standards in the CED and ETD graph by designation or title keyword."""
    eng = get_engine()
    nodes = eng.standards_graph.get("nodes", [])
    q_lower = q.lower()

    matches = []
    for n in nodes:
        desig = n.get("designation") or ""
        title = n.get("title") or ""
        dept = n.get("primary_department") or (n.get("source_departments") or ["UNKNOWN"])[0]

        if department and dept != department:
            continue

        if q_lower in desig.lower() or q_lower in title.lower():
            matches.append({
                "designation": desig,
                "title": title,
                "department": dept,
                "committee": n.get("committee"),
                "year": n.get("year"),
                "has_scope": bool(n.get("scope")),
            })
            if len(matches) >= top_k:
                break

    return {"query": q, "count": len(matches), "standards": matches}


@app.get("/api/v1/standards/{designation}")
def get_standard_details(designation: str):
    """Fetches complete node evidence, lifecycle, scope, and QCO status for an Indian Standard."""
    eng = get_engine()
    node = eng._find_graph_node(designation)
    if not node:
        raise HTTPException(status_code=404, detail=f"Standard '{designation}' not found in index.")

    life = eng.lifecycle_gate.resolve_edition(designation)
    reg = eng.regulatory_gate.evaluate_regulatory_status(designation)

    return {
        "designation": node.get("designation"),
        "title": node.get("title"),
        "department": node.get("primary_department") or (node.get("source_departments") or ["UNKNOWN"])[0],
        "committee": node.get("committee"),
        "ics_codes": node.get("ics_codes", []),
        "scope": node.get("scope"),
        "lifecycle": life,
        "regulatory": reg,
        "attributes": node.get("attributes", {}),
    }


# ── WebSocket Agent Streaming ──

@app.websocket("/api/v1/agent/stream")
async def websocket_agent_stream(websocket: WebSocket):
    """
    Streams live Agent execution, reasoning steps, tool calls, and validator gate verdict.
    """
    await websocket.accept()
    agent = get_agent()

    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            query = req.get("query", "")
            eval_date = req.get("evaluation_date")

            if not query:
                await websocket.send_json({"event": "error", "message": "Query cannot be empty"})
                continue

            await websocket.send_json({"event": "agent_start", "query": query, "timestamp": time.time()})
            await websocket.send_json({"event": "thought", "text": f"Analyzing procurement requirement: '{query}'"})

            # Stream execution
            try:
                res = agent.answer(query=query, evaluation_date=eval_date)
                for tc in res.get("tool_calls", []):
                    await websocket.send_json({
                        "event": "tool_call",
                        "tool": tc.get("tool"),
                        "arguments": tc.get("arguments"),
                        "status": tc.get("status"),
                    })

                await websocket.send_json({
                    "event": "validator_verdict",
                    "status": (res.get("agent_metadata") or {}).get("validator_status", "PASSED"),
                })
                await websocket.send_json({"event": "agent_finish", "final_answer": res})
            except Exception as ex:
                request_id = str(uuid.uuid4())[:8]
                logger.exception(f"WebSocket agent error [request_id={request_id}]")
                await websocket.send_json({"event": "error", "message": f"Agent could not process query. Reference: {request_id}"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=8000, reload=True)
