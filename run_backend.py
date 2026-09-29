"""
StandSpec AI — FastAPI Gateway Runner
Launches the REST & WebSocket server on http://127.0.0.1:8000
"""

import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print("  StandSpec AI — Indian Standards Procurement Recommendation Engine")
    print("  API Server starting on http://127.0.0.1:8000")
    print("  Interactive Swagger Docs: http://127.0.0.1:8000/docs")
    print("=" * 70)
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=8000, reload=False)
