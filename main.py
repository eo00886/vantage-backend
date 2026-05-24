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

app = FastAPI(title="VANTAGE Athletic Metrics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"message": "VANTAGE Athletic Metrics API", "status": "running", "version": "1.0.0"}

@app.post("/verify", response_model=VerifyResponse)
def verify_athlete(request: VerifyRequest):
    if not request.video_source:
        raise HTTPException(status_code=400, detail="Video source is required")
    
    result = detector.analyze_athlete(
        request.video_source, request.athlete_id,
        request.claimed_vertical, request.claimed_sprint
    )
    
    v_needs = 0 if (result['vertical_inches'] and result['vertical_confidence'] >= 90) else (2 if (result['vertical_inches'] and result['vertical_confidence'] >= 70) else (3 if result['vertical_inches'] else 4))
    s_needs = 0 if (result['sprint_seconds'] and result['sprint_confidence'] >= 90) else (2 if (result['sprint_seconds'] and result['sprint_confidence'] >= 70) else (3 if result['sprint_seconds'] else 4))
    
    return VerifyResponse(
        success=result['success'],
        vertical_inches=result.get('vertical_inches'),
        sprint_seconds=result.get('sprint_seconds'),
        vertical_confidence=result.get('vertical_confidence', 0),
        sprint_confidence=result.get('sprint_confidence', 0),
        vertical_needs_confirmations=v_needs,
        sprint_needs_confirmations=s_needs,
        vertical_clip_url=result.get('vertical_clip_url'),
        sprint_clip_url=result.get('sprint_clip_url'),
        thumbnail_url=result.get('thumbnail_url'),
        error=result.get('error')
    )

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1] or '.mp4'
        saved_path = f"./static/uploads/{file_id}{file_extension}"
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"video_url": f"/static/uploads/{file_id}{file_extension}", "success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/clip/{athlete_id}/{metric_type}")
def get_clip(athlete_id: int, metric_type: str):
    clip_path = f"./static/clips/athlete_{athlete_id}/{metric_type}.mp4"
    if os.path.exists(clip_path):
        return {"clip_url": f"/static/clips/athlete_{athlete_id}/{metric_type}.mp4", "exists": True}
    return {"clip_url": None, "exists": False}

@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
