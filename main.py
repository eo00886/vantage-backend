from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import uuid
import random
import shutil
from datetime import datetime

app = FastAPI(title="VANTAGE Athletic Metrics API", version="1.0.0")

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
os.makedirs("./static/thumbnails", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    
    # Generate realistic mock data
    if request.claimed_vertical and 20 <= request.claimed_vertical <= 60:
        vertical_inches = request.claimed_vertical + (random.random() - 0.5) * 2
        vertical_inches = round(max(20, min(60, vertical_inches)), 1)
        vertical_confidence = 85 + int(random.random() * 10)
    else:
        vertical_inches = round(random.uniform(28, 48), 1)
        vertical_confidence = 70 + int(random.random() * 20)
    
    if request.claimed_sprint and 3.8 <= request.claimed_sprint <= 5.5:
        sprint_seconds = request.claimed_sprint + (random.random() - 0.5) * 0.15
        sprint_seconds = round(max(3.8, min(5.5, sprint_seconds)), 2)
        sprint_confidence = 85 + int(random.random() * 10)
    else:
        sprint_seconds = round(random.uniform(4.2, 5.0), 2)
        sprint_confidence = 70 + int(random.random() * 20)
    
    # Adjust confidence based on claimed vs measured
    if request.claimed_vertical and abs(vertical_inches - request.claimed_vertical) > 3:
        vertical_confidence = max(55, vertical_confidence - 15)
    
    if request.claimed_sprint and abs(sprint_seconds - request.claimed_sprint) > 0.2:
        sprint_confidence = max(55, sprint_confidence - 15)
    
    # Determine needs_confirmations based on confidence
    vertical_needs = 0 if vertical_confidence >= 90 else (2 if vertical_confidence >= 70 else 3)
    sprint_needs = 0 if sprint_confidence >= 90 else (2 if sprint_confidence >= 70 else 3)
    
    # Generate clip URLs (mock)
    clip_dir = f"/static/clips/athlete_{request.athlete_id}"
    vertical_clip_url = f"{clip_dir}/vertical.mp4" if vertical_needs == 0 else None
    sprint_clip_url = f"{clip_dir}/sprint.mp4" if sprint_needs == 0 else None
    
    return VerifyResponse(
        success=True,
        vertical_inches=vertical_inches,
        sprint_seconds=sprint_seconds,
        vertical_confidence=vertical_confidence,
        sprint_confidence=sprint_confidence,
        vertical_needs_confirmations=vertical_needs,
        sprint_needs_confirmations=sprint_needs,
        vertical_clip_url=vertical_clip_url,
        sprint_clip_url=sprint_clip_url,
        thumbnail_url=None,
        error=None
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
    """Get clip URL for athlete (mock - returns demo clip)"""
    # Return a demo clip URL that will work with frontend
    return {"clip_url": None, "exists": False, "message": "Clips are generated client-side for demo"}

@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.0.0", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
