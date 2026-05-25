from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ========== ATHLETIC DETECTOR CLASS ==========
class AthleticDetector:
    """Simplified athletic metric detector - returns realistic mock data"""
    
    def __init__(self):
        pass
    
    def detect_platform(self, url: str) -> str:
        """Detect which platform the video URL is from"""
        patterns = {
            'instagram': r'instagram\.com/(?:p|reel|tv)',
            'youtube': r'(youtube\.com|youtu\.be)',
            'tiktok': r'tiktok\.com',
            'direct': r'\.(mp4|mov|avi|mkv|webm)$'
        }
        for platform, pattern in patterns.items():
            if re.search(pattern, url, re.IGNORECASE):
                return platform
        return 'unknown'
    
    def estimate_video_quality(self, url: str) -> float:
        """Estimate video quality based on URL patterns"""
        quality = 0.7
        if '/reel/' in url:
            quality += 0.1
        if 'instagram.com' in url or 'youtube.com' in url:
            quality += 0.05
        if 'tiktok.com' in url:
            quality += 0.03
        return min(0.95, quality)
    
    def generate_realistic_vertical(self, claimed_vertical: Optional[float], url: str) -> Dict:
        """Generate realistic vertical leap measurement"""
        quality = self.estimate_video_quality(url)
        
        if claimed_vertical and 20 <= claimed_vertical <= 60:
            variation = (random.random() - 0.5) * (1 - quality) * 6
            measured = claimed_vertical + variation
            measured = round(max(20, min(60, measured)), 1)
            difference = abs(measured - claimed_vertical)
            confidence = int(85 - (difference * 3) + (quality * 10))
            confidence = max(55, min(98, confidence))
        else:
            measured = round(random.uniform(28, 48), 1)
            confidence = int(65 + random.random() * 20)
        
        return {
            'vertical_inches': measured,
            'confidence': confidence,
            'needs_confirmations': 0 if confidence >= 90 else (2 if confidence >= 70 else 3)
        }
    
    def generate_realistic_sprint(self, claimed_sprint: Optional[float], url: str) -> Dict:
        """Generate realistic sprint time measurement"""
        quality = self.estimate_video_quality(url)
        
        if claimed_sprint and 3.8 <= claimed_sprint <= 5.8:
            variation = (random.random() - 0.5) * (1 - quality) * 0.2
            measured = claimed_sprint + variation
            measured = round(max(3.8, min(5.8, measured)), 2)
            difference = abs(measured - claimed_sprint)
            confidence = int(85 - (difference * 30) + (quality * 10))
            confidence = max(55, min(98, confidence))
        else:
            measured = round(random.uniform(4.2, 5.2), 2)
            confidence = int(65 + random.random() * 20)
        
        return {
            'sprint_seconds': measured,
            'confidence': confidence,
            'needs_confirmations': 0 if confidence >= 90 else (2 if confidence >= 70 else 3)
        }
    
    def analyze_athlete(self, video_source: str, athlete_id: int, 
                        claimed_vertical: Optional[float] = None, 
                        claimed_sprint: Optional[float] = None) -> Dict:
        """Complete athlete analysis with realistic mock data"""
        
        vertical_result = self.generate_realistic_vertical(claimed_vertical, video_source)
        sprint_result = self.generate_realistic_sprint(claimed_sprint, video_source)
        
        clip_dir = f"/static/clips/athlete_{athlete_id}"
        
        return {
            'success': True,
            'vertical_inches': vertical_result['vertical_inches'],
            'sprint_seconds': sprint_result['sprint_seconds'],
            'vertical_confidence': vertical_result['confidence'],
            'sprint_confidence': sprint_result['confidence'],
            'vertical_needs_confirmations': vertical_result['needs_confirmations'],
            'sprint_needs_confirmations': sprint_result['needs_confirmations'],
            'vertical_clip_url': f"{clip_dir}/vertical.mp4" if vertical_result['needs_confirmations'] == 0 else None,
            'sprint_clip_url': f"{clip_dir}/sprint.mp4" if sprint_result['needs_confirmations'] == 0 else None,
            'thumbnail_url': f"{clip_dir}/thumbnail.jpg" if vertical_result['needs_confirmations'] == 0 else None,
            'error': None
        }

detector = AthleticDetector()

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

# ========== SEED DATA ==========
SEED_ATHLETES = [
    {"id": 1, "name": "Marcus Thompson", "school": "Westlake High", "position": "SG", "jerseyNum": "23", "classYear": 2025, "flagged": False, "metrics": {"vertical": {"value": 42, "status": "verified", "verifications": 5, "confidence": 96}, "sprint": {"value": 4.38, "status": "verified", "verifications": 4, "confidence": 94}}, "trustScore": 94, "confirmations": ["Coach Miller", "Sarah Chen", "David Kim", "James Wilson", "Coach Thompson"], "views": 342, "hasClip": True},
    {"id": 2, "name": "Jaylen Carter", "school": "Mater Dei", "position": "PG", "jerseyNum": "11", "classYear": 2025, "flagged": False, "metrics": {"vertical": {"value": 38, "status": "verified", "verifications": 4, "confidence": 94}, "sprint": {"value": 4.45, "status": "pending", "verifications": 1, "confidence": 72}}, "trustScore": 91, "confirmations": ["Coach Miller", "Sarah Chen", "David Kim", "James Wilson"], "views": 189, "hasClip": True},
    {"id": 3, "name": "Elijah Williams", "school": "IMG Academy", "position": "SF", "jerseyNum": "7", "classYear": 2026, "flagged": False, "metrics": {"vertical": {"value": 44, "status": "verified", "verifications": 7, "confidence": 98}, "sprint": {"value": 4.28, "status": "verified", "verifications": 6, "confidence": 96}}, "trustScore": 96, "confirmations": ["Coach Miller", "Sarah Chen", "David Kim", "James Wilson", "Coach Thompson", "Mike Ross", "Lisa Wong"], "views": 567, "hasClip": True},
    {"id": 4, "name": "Tyler Brooks", "school": "Montverde Academy", "position": "PF", "jerseyNum": "34", "classYear": 2026, "flagged": False, "metrics": {"vertical": {"value": 35, "status": "pending", "verifications": 1, "confidence": 78}, "sprint": {"value": None, "status": "pending", "verifications": 0, "confidence": 0}}, "trustScore": 0, "confirmations": ["Coach Miller"], "views": 45, "hasClip": False},
    {"id": 5, "name": "Jordan Lee", "school": "Sierra Canyon", "position": "SG", "jerseyNum": "5", "classYear": 2025, "flagged": False, "metrics": {"vertical": {"value": 40, "status": "pending", "verifications": 1, "confidence": 72}, "sprint": {"value": 4.42, "status": "pending", "verifications": 0, "confidence": 68}}, "trustScore": 0, "confirmations": [], "views": 34, "hasClip": False},
    {"id": 6, "name": "Malik Henderson", "school": "Oak Hill Academy", "position": "PG", "jerseyNum": "1", "classYear": 2026, "flagged": False, "metrics": {"vertical": {"value": 37, "status": "pending", "verifications": 0, "confidence": 68}, "sprint": {"value": 4.35, "status": "pending", "verifications": 0, "confidence": 74}}, "trustScore": 0, "confirmations": [], "views": 28, "hasClip": True}
]

# ========== PERSISTENT STORAGE ==========
DATA_FILE = "./data/database.json"

def load_data() -> Dict:
    """Load data from JSON file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"athletes": {}, "scouts": {}}

def save_data(data: Dict):
    """Save data to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def init_database():
    """Initialize database with seed data if empty"""
    data = load_data()
    if not data["athletes"]:
        for athlete in SEED_ATHLETES:
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
    """Get all athletes for Discover page"""
    data = load_data()
    athletes = list(data["athletes"].values())
    athletes.sort(key=lambda x: x["id"], reverse=True)
    return athletes

@app.get("/athletes/{athlete_id}")
def get_athlete(athlete_id: int):
    """Get single athlete by ID"""
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
    """Get scout profile by ID"""
    data = load_data()
    scout = data["scouts"].get(scout_id)
    if not scout:
        raise HTTPException(status_code=404, detail="Scout not found")
    return scout

@app.post("/scout/create")
def create_scout(name: str):
    """Create a new scout profile"""
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
    """Confirm an athlete's metrics (community verification)"""
    data = load_data()
    athlete = data["athletes"].get(str(request.athlete_id))
    scout = data["scouts"].get(request.scout_id)
    
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    if not scout:
        raise HTTPException(status_code=404, detail="Scout not found")
    
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
    
    if athlete["metrics"]["sprint"]["status"] == "pending" and athlete["metrics"]["sprint"].get("value"):
        athlete["metrics"]["sprint"]["verifications"] += 1
        if athlete["metrics"]["sprint"]["verifications"] >= 3:
            athlete["metrics"]["sprint"]["status"] = "verified"
    
    athlete["confirmations"].append(request.scout_name)
    
    save_data(data)
    return {"success": True, "message": "Confirmed! +2 trust", "now_verified": verified}

@app.post("/watchlist")
def update_watchlist(request: WatchlistRequest):
    """Add or remove athlete from scout watchlist"""
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
    """Get full watchlist with athlete details"""
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
    """AI analysis of athlete video"""
    if not request.video_source:
        raise HTTPException(status_code=400, detail="Video source is required")
    
    result = detector.analyze_athlete(
        request.video_source,
        request.athlete_id,
        request.claimed_vertical,
        request.claimed_sprint
    )
    
    if result['success']:
        data = load_data()
        new_athlete = {
            "id": request.athlete_id,
            "name": request.athlete_name,
            "school": request.athlete_school,
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
    """Handle direct video uploads"""
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

@app.get("/")
def root():
    return {
        "message": "VANTAGE Athletic Metrics API",
        "status": "running",
        "endpoints": ["/athletes", "/verify", "/confirm", "/watchlist", "/scout/{id}"]
    }

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
