from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import uuid
import shutil
from datetime import datetime
from vertical_detector import AthleticDetector

app = FastAPI(title="VANTAGE Athletic Metrics API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
os.makedirs("./static/clips", exist_ok=True)
os.makedirs("./static/uploads", exist_ok=True)
os.makedirs("./static/thumbnails", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize detector
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
        "version": "1.0.0",
        "endpoints": ["/verify", "/upload-video", "/health"]
    }

@app.post("/verify", response_model=VerifyResponse)
def verify_athlete(request: VerifyRequest):
    if not request.video_source:
        raise HTTPException(status_code=400, detail="Video source is required")
    
    result = detector.analyze_athlete(
        request.video_source,
        request.athlete_id,
        request.claimed_vertical,
        request.claimed_sprint
    )
    
    return VerifyResponse(
        success=result['success'],
        vertical_inches=result.get('vertical_inches'),
        sprint_seconds=result.get('sprint_seconds'),
        vertical_confidence=result.get('vertical_confidence', 0),
        sprint_confidence=result.get('sprint_confidence', 0),
        vertical_needs_confirmations=result.get('vertical_needs_confirmations', 3),
        sprint_needs_confirmations=result.get('sprint_needs_confirmations', 3),
        vertical_clip_url=result.get('vertical_clip_url'),
        sprint_clip_url=result.get('sprint_clip_url'),
        thumbnail_url=result.get('thumbnail_url'),
        error=result.get('error')
    )

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """Handle direct video uploads"""
    try:
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1] or '.mp4'
        saved_path = f"./static/uploads/{file_id}{file_extension}"
        
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        video_url = f"/static/uploads/{file_id}{file_extension}"
        
        return {"video_url": video_url, "success": True, "message": "Video uploaded successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/clip/{athlete_id}/{metric_type}")
def get_clip(athlete_id: int, metric_type: str):
    """Get clip URL for athlete - returns mock data (frontend generates actual videos)"""
    clip_path = f"./static/clips/athlete_{athlete_id}/{metric_type}.mp4"
    if os.path.exists(clip_path):
        return {"clip_url": f"/static/clips/athlete_{athlete_id}/{metric_type}.mp4", "exists": True}
    return {"clip_url": None, "exists": False, "message": "Clip not yet generated"}

@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.0.0", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
