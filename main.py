from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# Mount static files for clips and thumbnails
os.makedirs("./static/clips", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

detector = AthleticDetector()

# In-memory athlete storage (replace with database in production)
athletes_db = {}

class VerifyBothRequest(BaseModel):
    instagram_url: str
    athlete_id: int
    athlete_name: str
    athlete_school: str
    athlete_position: str
    claimed_vertical: Optional[float] = None
    claimed_sprint: Optional[float] = None

class VerifyResponse(BaseModel):
    success: bool
    vertical_inches: Optional[float]
    sprint_seconds: Optional[float]
    vertical_confidence: int
    sprint_confidence: int
    vertical_needs_confirmations: int
    sprint_needs_confirmations: int
    vertical_clip_url: Optional[str] = None
    sprint_clip_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    error: Optional[str] = None

@app.get("/")
def root():
    return {
        "message": "VANTAGE Athletic Metrics API",
        "status": "running",
        "version": "1.0.0",
        "sport": "Basketball (MVP)",
        "features": ["Vertical Leap Detection", "40-Yard Sprint Detection", "Video Clip Extraction", "Thumbnail Generation"]
    }

@app.post("/verify-both", response_model=VerifyResponse)
def verify_both(request: VerifyBothRequest):
    if not request.instagram_url:
        raise HTTPException(status_code=400, detail="Instagram URL is required")
    
    # Store athlete info
    athletes_db[request.athlete_id] = {
        'name': request.athlete_name,
        'school': request.athlete_school,
        'position': request.athlete_position
    }
    
    # Run analysis
    result = detector.analyze_both(
        request.instagram_url,
        request.athlete_id,
        request.claimed_vertical,
        request.claimed_sprint
    )
    
    v = result['vertical']
    s = result['sprint']
    
    v_needs = 0 if (v['success'] and v['vertical_inches'] and v['confidence'] >= 90) else (2 if (v['success'] and v['vertical_inches'] and v['confidence'] >= 70) else (3 if v['success'] else 4))
    s_needs = 0 if (s['success'] and s['sprint_seconds'] and s['confidence'] >= 90) else (2 if (s['success'] and s['sprint_seconds'] and s['confidence'] >= 70) else (3 if s['success'] else 4))
    
    return VerifyResponse(
        success=v['success'] or s['success'],
        vertical_inches=v.get('vertical_inches'),
        sprint_seconds=s.get('sprint_seconds'),
        vertical_confidence=v.get('confidence', 0),
        sprint_confidence=s.get('confidence', 0),
        vertical_needs_confirmations=v_needs,
        sprint_needs_confirmations=s_needs,
        vertical_clip_url=v.get('clip_path'),
        sprint_clip_url=s.get('clip_path'),
        thumbnail_url=v.get('thumbnail_path'),
        error=v.get('error') or s.get('error')
    )

@app.get("/athlete/{athlete_id}/clip/{metric_type}")
def get_athlete_clip(athlete_id: int, metric_type: str):
    """Return the highlight clip URL for an athlete's metric"""
    clip_path = f"./static/clips/athlete_{athlete_id}/{metric_type}.mp4"
    
    if os.path.exists(clip_path):
        return {"clip_url": f"/static/clips/athlete_{athlete_id}/{metric_type}.mp4", "exists": True}
    else:
        return {"clip_url": None, "exists": False, "message": "Clip not yet generated"}

@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.0.0", "sport": "Basketball"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
