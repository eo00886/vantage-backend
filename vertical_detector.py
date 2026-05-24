import random
import re
from typing import Dict, Tuple, Optional

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
            # Start with claimed value, add realistic variation
            variation = (random.random() - 0.5) * (1 - quality) * 6
            measured = claimed_vertical + variation
            measured = round(max(20, min(60, measured)), 1)
            
            # Calculate confidence based on how close measured is to claimed
            difference = abs(measured - claimed_vertical)
            confidence = int(85 - (difference * 3) + (quality * 10))
            confidence = max(55, min(98, confidence))
        else:
            # Generate random realistic vertical between 28-48 inches
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
        
        # Generate mock clip URLs (frontend handles actual video generation)
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
