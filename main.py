from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import uuid
import shutil
from vertical_detector import AthleticDetector

app = FastAPI(title="VANTAGE Athletic Metrics API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
os.makedirs("./static/clips", exist_ok=True)
os.makedirs("./static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

detector = AthleticDetector()

class VerifyRequest(BaseModel):
    video_source: str
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
        "version": "2.0.0",
        "sport": "Basketball (MVP)",
        "supported_platforms": ["Instagram", "YouTube", "TikTok", "Twitter/X", "Direct URL", "File Upload", "Camera Capture"],
        "features": ["Vertical Leap Detection", "40-Yard Sprint Detection", "Video Clip Extraction", "Thumbnail Generation"]
    }

@app.post("/verify", response_model=VerifyResponse)
def verify_athlete(request: VerifyRequest):
    if not request.video_source:
        raise HTTPException(status_code=400, detail="Video source is required")
    
    result = detector.analyze_both(
        request.video_source,
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

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """Handle direct video uploads"""
    try:
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        if not file_extension:
            file_extension = '.mp4'
        saved_path = f"./static/uploads/{file_id}{file_extension}"
        
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        video_url = f"/static/uploads/{file_id}{file_extension}"
        
        return {"video_url": video_url, "success": True, "message": "Video uploaded successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/health")
def health():
    return {"status": "healthy", "version": "2.0.0", "sport": "Basketball"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
