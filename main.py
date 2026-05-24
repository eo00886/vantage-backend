from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import random
import re

app = FastAPI(title="VANTAGE Athletic Metrics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def extract_shortcode(url: str) -> Optional[str]:
    """Extract Instagram shortcode from URL"""
    match = re.search(r'instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url)
    return match.group(1) if match else None

def calculate_video_quality(url: str) -> float:
    """Estimate video quality based on URL patterns"""
    quality = 0.7
    if '/reel/' in url:
        quality += 0.1
    if 'instagram.com' in url:
        quality += 0.05
    # Shorter shortcodes often indicate older/less quality videos
    shortcode = extract_shortcode(url)
    if shortcode and len(shortcode) > 8:
        quality += 0.05
    return min(0.95, quality)

def generate_realistic_vertical(claimed: Optional[float], url: str) -> dict:
    """Generate realistic vertical leap measurement (mock AI)"""
    quality = calculate_video_quality(url)
    
    if claimed and 20 <= claimed <= 60:
        # Base measurement close to claimed
        variation = (random.random() - 0.5) * (1 - quality) * 8
        measured = claimed + variation
    else:
        # Generate random realistic vertical between 28-48 inches
        measured = random.uniform(28, 48)
    
    measured = round(max(20, min(60, measured)), 1)
    
    # Calculate confidence based on quality and how reasonable the measurement is
    confidence = int(55 + (quality * 35) + (random.random() * 10))
    confidence = min(98, max(55, confidence))
    
    # Adjust confidence if claimed is far off
    if claimed and abs(measured - claimed) > 5:
        confidence = max(55, confidence - 15)
    
    return {
        'success': True,
        'vertical_inches': measured,
        'confidence': confidence,
        'error': None
    }

def generate_realistic_sprint(claimed: Optional[float], url: str) -> dict:
    """Generate realistic sprint time measurement (mock AI)"""
    quality = calculate_video_quality(url)
    
    if claimed and 3.8 <= claimed <= 5.5:
        variation = (random.random() - 0.5) * (1 - quality) * 0.3
        measured = claimed + variation
    else:
        measured = random.uniform(4.2, 5.0)
    
    measured = round(max(3.8, min(5.5, measured)), 2)
    
    confidence = int(55 + (quality * 35) + (random.random() * 10))
    confidence = min(98, max(55, confidence))
    
    if claimed and abs(measured - claimed) > 0.3:
        confidence = max(55, confidence - 15)
    
    return {
        'success': True,
        'sprint_seconds': measured,
        'confidence': confidence,
        'error': None
    }

@app.get("/")
def root():
    return {
        "message": "VANTAGE Athletic Metrics API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": [
            "POST /verify-vertical",
            "POST /verify-sprint",
            "POST /verify-both",
            "GET /health"
        ],
        "note": "This is a demo API with realistic mock data. For production with real AI, deploy the OpenCV version."
    }

@app.post("/verify-vertical", response_model=VerticalResponse)
def verify_vertical(request: VerifyVerticalRequest):
    if not request.instagram_url:
        raise HTTPException(status_code=400, detail="Instagram URL is required")
    
    # Validate URL format
    if not extract_shortcode(request.instagram_url):
        return VerticalResponse(
            success=False,
            vertical_inches=None,
            confidence=0,
            error="Invalid Instagram URL. Please enter a valid Instagram post/reel URL.",
            needs_confirmations=4
        )
    
    result = generate_realistic_vertical(request.claimed_vertical, request.instagram_url)
    
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
    
    if not extract_shortcode(request.instagram_url):
        return SprintResponse(
            success=False,
            sprint_seconds=None,
            confidence=0,
            error="Invalid Instagram URL. Please enter a valid Instagram post/reel URL.",
            needs_confirmations=4
        )
    
    result = generate_realistic_sprint(request.claimed_sprint, request.instagram_url)
    
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
    
    vertical = generate_realistic_vertical(request.claimed_vertical, request.instagram_url)
    sprint = generate_realistic_sprint(request.claimed_sprint, request.instagram_url)
    
    v_conf = vertical['confidence']
    s_conf = sprint['confidence']
    
    v_needs = 0 if (vertical['success'] and v_conf >= 90) else (2 if (vertical['success'] and v_conf >= 70) else (3 if vertical['success'] else 4))
    s_needs = 0 if (sprint['success'] and s_conf >= 90) else (2 if (sprint['success'] and s_conf >= 70) else (3 if sprint['success'] else 4))
    
    return BothResponse(
        vertical=VerticalResponse(
            success=vertical['success'],
            vertical_inches=vertical.get('vertical_inches'),
            confidence=vertical['confidence'],
            error=vertical.get('error'),
            needs_confirmations=v_needs
        ),
        sprint=SprintResponse(
            success=sprint['success'],
            sprint_seconds=sprint.get('sprint_seconds'),
            confidence=sprint['confidence'],
            error=sprint.get('error'),
            needs_confirmations=s_needs
        )
    )

@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
