from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
from vertical_detector import AthleticDetector

app = FastAPI(title="VANTAGE Athletic Metrics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = AthleticDetector()

class VerifyVerticalRequest(BaseModel):
    instagram_url: str
    claimed_vertical: Optional[float] = None

class VerifySprintRequest(BaseModel):
    instagram_url: str
    claimed_sprint: Optional[float] = None

class VerifyBothRequest(BaseModel):
    instagram_url: str
    claimed_vertical: Optional[float] = None
    claimed_sprint: Optional[float] = None

class VerticalResponse(BaseModel):
    success: bool
    vertical_inches: Optional[float]
    confidence: int
    error: Optional[str]
    needs_confirmations: int

class SprintResponse(BaseModel):
    success: bool
    sprint_seconds: Optional[float]
    confidence: int
    error: Optional[str]
    needs_confirmations: int

class BothResponse(BaseModel):
    vertical: VerticalResponse
    sprint: SprintResponse

@app.get("/")
def root():
    return {
        "message": "VANTAGE Athletic Metrics API",
        "status": "running",
        "endpoints": [
            "POST /verify-vertical",
            "POST /verify-sprint",
            "POST /verify-both",
            "GET /health"
        ]
    }

@app.post("/verify-vertical", response_model=VerticalResponse)
def verify_vertical(request: VerifyVerticalRequest):
    if not request.instagram_url:
        raise HTTPException(status_code=400, detail="Instagram URL is required")
    
    result = detector.analyze_vertical(request.instagram_url, request.claimed_vertical)
    
    if result['success'] and result['vertical_inches']:
        confidence = result['confidence']
        if confidence >= 90:
            needs_confirmations = 0
        elif confidence >= 70:
            needs_confirmations = 2
        else:
            needs_confirmations = 3
    else:
        needs_confirmations = 4
    
    return VerticalResponse(
        success=result['success'],
        vertical_inches=result['vertical_inches'],
        confidence=result['confidence'],
        error=result.get('error'),
        needs_confirmations=needs_confirmations
    )

@app.post("/verify-sprint", response_model=SprintResponse)
def verify_sprint(request: VerifySprintRequest):
    if not request.instagram_url:
        raise HTTPException(status_code=400, detail="Instagram URL is required")
    
    result = detector.analyze_sprint(request.instagram_url, request.claimed_sprint)
    
    if result['success'] and result['sprint_seconds']:
        confidence = result['confidence']
        if confidence >= 90:
            needs_confirmations = 0
        elif confidence >= 70:
            needs_confirmations = 2
        else:
            needs_confirmations = 3
    else:
        needs_confirmations = 4
    
    return SprintResponse(
        success=result['success'],
        sprint_seconds=result['sprint_seconds'],
        confidence=result['confidence'],
        error=result.get('error'),
        needs_confirmations=needs_confirmations
    )

@app.post("/verify-both", response_model=BothResponse)
def verify_both(request: VerifyBothRequest):
    if not request.instagram_url:
        raise HTTPException(status_code=400, detail="Instagram URL is required")
    
    result = detector.analyze_both(
        request.instagram_url,
        request.claimed_vertical,
        request.claimed_sprint
    )
    
    v = result['vertical']
    s = result['sprint']
    
    v_needs = 0 if (v['success'] and v['vertical_inches'] and v['confidence'] >= 90) else (2 if (v['success'] and v['vertical_inches'] and v['confidence'] >= 70) else (3 if v['success'] else 4))
    s_needs = 0 if (s['success'] and s['sprint_seconds'] and s['confidence'] >= 90) else (2 if (s['success'] and s['sprint_seconds'] and s['confidence'] >= 70) else (3 if s['success'] else 4))
    
    return BothResponse(
        vertical=VerticalResponse(
            success=v['success'],
            vertical_inches=v.get('vertical_inches'),
            confidence=v.get('confidence', 0),
            error=v.get('error'),
            needs_confirmations=v_needs
        ),
        sprint=SprintResponse(
            success=s['success'],
            sprint_seconds=s.get('sprint_seconds'),
            confidence=s.get('confidence', 0),
            error=s.get('error'),
            needs_confirmations=s_needs
        )
    )

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
