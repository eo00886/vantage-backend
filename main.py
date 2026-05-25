from fastapi import FastAPI, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import os
import uuid
import shutil
import json
import random
import re
from datetime import datetime
from pathlib import Path

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
os.makedirs("./data", exist_ok=True)

# Mount static files for serving clips
app.mount("/static", StaticFiles(directory="static"), name="static")

# ========== DATA MODELS ==========
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

class ConfirmRequest(BaseModel):
    athlete_id: int
    scout_id: str
    scout_name: str

class WatchlistRequest(BaseModel):
    scout_id: str
    athlete_id: int

# ========== ATHLETIC DETECTOR ==========
class AthleticDetector:
    def __init__(self):
        pass
    
    def analyze_athlete(self, video_source: str, athlete_id: int, claimed_vertical: Optional[float], claimed_sprint: Optional[float]) -> Dict:
        """Analyze athlete video and generate metrics"""
        
        # Generate realistic metrics based on claimed values
        if claimed_vertical and 20 <= claimed_vertical <= 60:
            vertical = round(claimed_vertical + (random.random() - 0.5) * 2, 1)
            vertical = max(20, min(60, vertical))
            vert_confidence = min(98, max(65, 85 - abs(vertical - claimed_vertical) * 2))
        else:
            vertical = round(random.uniform(28, 48), 1)
            vert_confidence = random.randint(65, 92)
        
        if claimed_sprint and 3.8 <= claimed_sprint <= 5.8:
            sprint = round(claimed_sprint + (random.random() - 0.5) * 0.15, 2)
            sprint = max(3.8, min(5.8, sprint))
            sprint_confidence = min(98, max(65, 85 - abs(sprint - claimed_sprint) * 30))
        else:
            sprint = round(random.uniform(4.2, 5.2), 2)
            sprint_confidence = random.randint(65, 92)
        
        # Generate clip URLs (create placeholder files)
        clip_dir = f"./static/clips/athlete_{athlete_id}"
        os.makedirs(clip_dir, exist_ok=True)
        
        # Create placeholder clip files (in production, these would be actual videos)
        vertical_clip_path = f"{clip_dir}/vertical.mp4"
        sprint_clip_path = f"{clip_dir}/sprint.mp4"
        thumbnail_path = f"{clip_dir}/thumbnail.jpg"
        
        # Create simple placeholder files
        with open(vertical_clip_path, 'w') as f:
            f.write(f"Vertical clip placeholder for athlete {athlete_id}")
        with open(sprint_clip_path, 'w') as f:
            f.write(f"Sprint clip placeholder for athlete {athlete_id}")
        
        # Create a simple SVG thumbnail
        svg_content = f'''<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
            <rect width="400" height="400" fill="#1e3a5f"/>
            <circle cx="200" cy="200" r="100" fill="rgba(255,255,255,0.1)"/>
            <text x="200" y="200" text-anchor="middle" fill="white" font-size="40" font-family="Arial">🏀</text>
            <text x="200" y="280" text-anchor="middle" fill="#3B82F6" font-size="20">Vertical: {vertical}"</text>
            <text x="200" y="320" text-anchor="middle" fill="#8B5CF6" font-size="20">Sprint: {sprint}s</text>
        </svg>'''
        with open(thumbnail_path, 'w') as f:
            f.write(svg_content)
        
        return {
            'success': True,
            'vertical_inches': vertical,
            'sprint_seconds': sprint,
            'vertical_confidence': vert_confidence,
            'sprint_confidence': sprint_confidence,
            'vertical_needs_confirmations': 3 if vert_confidence < 90 else 0,
            'sprint_needs_confirmations': 3 if sprint_confidence < 90 else 0,
            'vertical_clip_url': f"/static/clips/athlete_{athlete_id}/vertical.mp4",
            'sprint_clip_url': f"/static/clips/athlete_{athlete_id}/sprint.mp4",
            'thumbnail_url': f"/static/clips/athlete_{athlete_id}/thumbnail.jpg",
            'error': None
        }

detector = AthleticDetector()

# ========== DATABASE FUNCTIONS ==========
DATA_FILE = "./data/database.json"

def load_data() -> Dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"athletes": {}, "scouts": {}}

def save_data(data: Dict):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Seed athletes (matching frontend exactly)
SEED_ATHLETES = [
    {"id": 1, "name": "Marcus Thompson", "school": "Westlake High", "position": "SG", "jerseyNum": "23", "classYear": 2025, "flagged": False, "metrics": {"vertical": {"value": 42, "status": "verified", "verifications": 5, "confidence": 96}, "sprint": {"value": 4.38, "status": "verified", "verifications": 4, "confidence": 94}}, "trustScore": 94, "confirmations": ["Coach Miller", "Sarah Chen", "David Kim", "James Wilson", "Coach Thompson"], "views": 342, "hasClip": True},
    {"id": 2, "name": "Jaylen Carter", "school": "Mater Dei", "position": "PG", "jerseyNum": "11", "classYear": 2025, "flagged": False, "metrics": {"vertical": {"value": 38, "status": "verified", "verifications": 4, "confidence": 94}, "sprint": {"value": 4.45, "status": "pending", "verifications": 1, "confidence": 72}}, "trustScore": 91, "confirmations": ["Coach Miller", "Sarah Chen", "David Kim", "James Wilson"], "views": 189, "hasClip": True},
    {"id": 3, "name": "Elijah Williams", "school": "IMG Academy", "position": "SF", "jerseyNum": "7", "classYear": 2026, "flagged": False, "metrics": {"vertical": {"value": 44, "status": "verified", "verifications": 7, "confidence": 98}, "sprint": {"value": 4.28, "status": "verified", "verifications": 6, "confidence": 96}}, "trustScore": 96, "confirmations": ["Coach Miller", "Sarah Chen", "David Kim", "James Wilson", "Coach Thompson", "Mike Ross", "Lisa Wong"], "views": 567, "hasClip": True},
    {"id": 4, "name": "Tyler Brooks", "school": "Montverde Academy", "position": "PF", "jerseyNum": "34", "classYear": 2026, "flagged": False, "metrics": {"vertical": {"value": 35, "status": "pending", "verifications": 1, "confidence": 78}, "sprint": {"value": None, "status": None, "verifications": 0, "confidence": 0}}, "trustScore": 0, "confirmations": ["Coach Miller"], "views": 45, "hasClip": False},
    {"id": 5, "name": "Jordan Lee", "school": "Sierra Canyon", "position": "SG", "jerseyNum": "5", "classYear": 2025, "flagged": False, "metrics": {"vertical": {"value": 40, "status": "pending", "verifications": 1, "confidence": 72}, "sprint": {"value": 4.42, "status": "pending", "verifications": 0, "confidence": 68}}, "trustScore": 0, "confirmations": [], "views": 34, "hasClip": False},
    {"id": 6, "name": "Malik Henderson", "school": "Oak Hill Academy", "position": "PG", "jerseyNum": "1", "classYear": 2026, "flagged": False, "metrics": {"vertical": {"value": 37, "status": "pending", "verifications": 0, "confidence": 68}, "sprint": {"value": 4.35, "status": "pending", "verifications": 0, "confidence": 74}}, "trustScore": 0, "confirmations": [], "views": 28, "hasClip": False}
]

def init_database():
    data = load_data()
    if not data["athletes"]:
        for athlete in SEED_ATHLETES:
            # Ensure clip directories exist for athletes with clips
            if athlete.get("hasClip", True):
                clip_dir = f"./static/clips/athlete_{athlete['id']}"
                os.makedirs(clip_dir, exist_ok=True)
            data["athletes"][str(athlete["id"])] = athlete
    if not data["scouts"]:
        data["scouts"]["scout_001"] = {
            "id": "scout_001",
            "name": "Demo Scout",
            "trustScore": 85,
            "confirmationsMade": 3,
            "streak": 3,
            "watchlist": [1, 3],
            "confirmedAthleteIds": [1],
            "challengedAthleteIds": []
        }
    save_data(data)

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    init_database()

# ========== ATHLETE ENDPOINTS ==========
@app.get("/athletes")
def get_all_athletes():
    data = load_data()
    athletes = list(data["athletes"].values())
    athletes.sort(key=lambda x: x["id"], reverse=True)
    return athletes

@app.get("/athletes/{athlete_id}")
def get_athlete(athlete_id: int):
    data = load_data()
    athlete = data["athletes"].get(str(athlete_id))
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    athlete["views"] = athlete.get("views", 0) + 1
    save_data(data)
    return athlete

# ========== SCOUT ENDPOINTS ==========
@app.get("/scout/{scout_id}")
def get_scout_profile(scout_id: str):
    data = load_data()
    scout = data["scouts"].get(scout_id)
    if not scout:
        raise HTTPException(status_code=404, detail="Scout not found")
    return scout

@app.post("/scout/create")
def create_scout(name: str):
    data = load_data()
    scout_id = f"scout_{uuid.uuid4().hex[:8]}"
    new_scout = {
        "id": scout_id,
        "name": name,
        "trustScore": 85,
        "confirmationsMade": 0,
        "streak": 0,
        "watchlist": [],
        "confirmedAthleteIds": [],
        "challengedAthleteIds": []
    }
    data["scouts"][scout_id] = new_scout
    save_data(data)
    return new_scout

@app.post("/confirm")
def confirm_athlete(request: ConfirmRequest):
    data = load_data()
    athlete = data["athletes"].get(str(request.athlete_id))
    scout = data["scouts"].get(request.scout_id)
    
    if not athlete or not scout:
        raise HTTPException(status_code=404, detail="Not found")
    
    if request.athlete_id in scout["confirmedAthleteIds"]:
        raise HTTPException(status_code=400, detail="Already confirmed")
    
    scout["confirmedAthleteIds"].append(request.athlete_id)
    scout["confirmationsMade"] += 1
    scout["trustScore"] = min(100, scout["trustScore"] + 2)
    scout["streak"] += 1
    
    verified = False
    if athlete["metrics"]["vertical"]["status"] == "pending":
        athlete["metrics"]["vertical"]["verifications"] += 1
        if athlete["metrics"]["vertical"]["verifications"] >= 3:
            athlete["metrics"]["vertical"]["status"] = "verified"
            athlete["trustScore"] = max(athlete["trustScore"], 85)
            verified = True
    
    if athlete["metrics"]["sprint"].get("value") and athlete["metrics"]["sprint"]["status"] == "pending":
        athlete["metrics"]["sprint"]["verifications"] += 1
        if athlete["metrics"]["sprint"]["verifications"] >= 3:
            athlete["metrics"]["sprint"]["status"] = "verified"
    
    athlete["confirmations"].append(request.scout_name)
    save_data(data)
    return {"success": True, "message": "Confirmed! +2 trust", "now_verified": verified}

@app.post("/watchlist")
def update_watchlist(request: WatchlistRequest):
    data = load_data()
    scout = data["scouts"].get(request.scout_id)
    
    if not scout:
        raise HTTPException(status_code=404, detail="Scout not found")
    
    if request.athlete_id in scout["watchlist"]:
        scout["watchlist"].remove(request.athlete_id)
        message = "Removed from watchlist"
    else:
        scout["watchlist"].append(request.athlete_id)
        message = "Added to watchlist"
    
    save_data(data)
    return {"success": True, "message": message, "watchlist": scout["watchlist"]}

@app.get("/watchlist/{scout_id}")
def get_watchlist(scout_id: str):
    data = load_data()
    scout = data["scouts"].get(scout_id)
    if not scout:
        raise HTTPException(status_code=404, detail="Scout not found")
    
    watchlist_athletes = []
    for athlete_id in scout["watchlist"]:
        athlete = data["athletes"].get(str(athlete_id))
        if athlete and not athlete.get("flagged", False):
            watchlist_athletes.append(athlete)
    return watchlist_athletes

# ========== VERIFICATION ENDPOINTS ==========
@app.post("/verify", response_model=VerifyResponse)
def verify_athlete(request: VerifyRequest):
    if not request.video_source:
        raise HTTPException(status_code=400, detail="Video source is required")
    
    result = detector.analyze_athlete(
        request.video_source, request.athlete_id,
        request.claimed_vertical, request.claimed_sprint
    )
    
    if result['success']:
        data = load_data()
        new_athlete = {
            "id": request.athlete_id,
            "name": request.athlete_name,
            "school": request.athlete_school or "Not specified",
            "position": request.athlete_position,
            "jerseyNum": str(random.randint(0, 99)),
            "classYear": 2026,
            "flagged": False,
            "metrics": {
                "vertical": {
                    "value": result['vertical_inches'],
                    "status": "pending" if result['vertical_needs_confirmations'] > 0 else "verified",
                    "verifications": 0,
                    "confidence": result['vertical_confidence']
                },
                "sprint": {
                    "value": result['sprint_seconds'],
                    "status": "pending" if result['sprint_needs_confirmations'] > 0 else "verified",
                    "verifications": 0,
                    "confidence": result['sprint_confidence']
                }
            },
            "trustScore": 0 if result['vertical_needs_confirmations'] > 0 else 85,
            "confirmations": [],
            "views": 0,
            "hasClip": True
        }
        data["athletes"][str(request.athlete_id)] = new_athlete
        save_data(data)
    
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
    try:
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1] or '.mp4'
        saved_path = f"./static/uploads/{file_id}{file_extension}"
        
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        video_url = f"/static/uploads/{file_id}{file_extension}"
        return {"video_url": video_url, "success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ========== CLIP SERVING ==========
@app.get("/clip/{athlete_id}/{metric_type}")
def get_clip(athlete_id: int, metric_type: str):
    clip_path = f"./static/clips/athlete_{athlete_id}/{metric_type}.mp4"
    if os.path.exists(clip_path):
        return FileResponse(clip_path)
    return {"exists": False, "message": "Clip not yet generated"}

@app.get("/thumbnail/{athlete_id}")
def get_thumbnail(athlete_id: int):
    thumb_path = f"./static/clips/athlete_{athlete_id}/thumbnail.jpg"
    if os.path.exists(thumb_path):
        return FileResponse(thumb_path)
    return {"exists": False}

# ========== HEALTH & ROOT ==========
@app.get("/")
def root():
    return {
        "message": "VANTAGE Athletic Metrics API",
        "status": "running",
        "endpoints": ["/athletes", "/verify", "/confirm", "/watchlist", "/scout/{id}", "/clip/{id}/{type}"]
    }

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
