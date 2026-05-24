import cv2
import numpy as np
import requests
import os
import tempfile
import re
from typing import Dict, Tuple, Optional

class AthleticDetector:
    """AI-powered athletic metric detection from Instagram videos"""
    
    RIM_HEIGHT_INCHES = 120  # 10 feet
    SPRINT_DISTANCE_YARDS = 40
    SPRINT_DISTANCE_FEET = 120
    BASKETBALL_COURT_LENGTH_FT = 94  # Full court
    BASKETBALL_HALF_COURT_FT = 47
    FOOTBALL_FIELD_HASH_MARKS_YARDS = 1  # Between hash marks
    
    def __init__(self):
        pass
        
    def download_instagram_video(self, url: str) -> Optional[str]:
        """Download video from Instagram URL"""
        try:
            shortcode_match = re.search(r'instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url)
            if not shortcode_match:
                return None
            shortcode = shortcode_match.group(1)
            
            video_url = f"https://www.instagram.com/p/{shortcode}/media/?size=l"
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_path = temp_file.name
            temp_file.close()
            
            response = requests.get(video_url, stream=True, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return temp_path
            return None
        except Exception as e:
            print(f"Download error: {e}")
            return None
    
    def extract_frames(self, video_path: str, frame_interval: int = 3) -> list:
        """Extract frames from video for analysis"""
        cap = cv2.VideoCapture(video_path)
        frames = []
        frame_count = 0
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % frame_interval == 0:
                frames.append(frame)
            frame_count += 1
        
        cap.release()
        return frames, fps
    
    # ============================================
    # VERTICAL LEAP DETECTION
    # ============================================
    
    def detect_rim(self, frame: np.ndarray) -> Tuple[Optional[int], Optional[int], float]:
        """Detect basketball rim position in frame"""
        try:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            lower_orange = np.array([0, 100, 100])
            upper_orange = np.array([20, 255, 255])
            
            mask = cv2.inRange(hsv, lower_orange, upper_orange)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                largest = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(largest)
                
                if area > 100:
                    x, y, w, h = cv2.boundingRect(largest)
                    rim_center_y = y + h // 2
                    rim_center_x = x + w // 2
                    confidence = min(0.95, area / 5000)
                    return rim_center_x, rim_center_y, confidence
            return None, None, 0.0
        except Exception as e:
            return None, None, 0.0
    
    def detect_feet(self, frame: np.ndarray) -> Tuple[Optional[int], float]:
        """Detect player's feet position in frame"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            vertical_projection = np.sum(edges, axis=1)
            
            height = frame.shape[0]
            feet_y = None
            
            for y in range(height - 1, height // 2, -1):
                if vertical_projection[y] > 50:
                    feet_y = y
                    break
            
            if feet_y:
                confidence = min(0.9, vertical_projection[feet_y] / 200)
                return feet_y, confidence
            return None, 0.0
        except Exception as e:
            return None, 0.0
    
    def find_best_vertical_frames(self, frames: list) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], float]:
        """Identify takeoff and peak jump frames"""
        feet_positions = []
        for frame in frames:
            feet_y, _ = self.detect_feet(frame)
            feet_positions.append(feet_y)
        
        lowest = float('inf')
        lowest_idx = None
        highest = -float('inf')
        highest_idx = None
        
        for i, pos in enumerate(feet_positions):
            if pos:
                if pos < lowest:
                    lowest = pos
                    lowest_idx = i
                if pos > highest:
                    highest = pos
                    highest_idx = i
        
        if lowest_idx is not None and highest_idx is not None:
            return frames[lowest_idx], frames[highest_idx], 0.8
        return None, None, 0
    
    def calculate_vertical(self, takeoff_frame: np.ndarray, peak_frame: np.ndarray) -> Dict:
        """Calculate vertical leap from takeoff and peak frames"""
        
        _, rim_y_takeoff, rim_conf_takeoff = self.detect_rim(takeoff_frame)
        _, rim_y_peak, rim_conf_peak = self.detect_rim(peak_frame)
        feet_y_takeoff, feet_conf_takeoff = self.detect_feet(takeoff_frame)
        feet_y_peak, feet_conf_peak = self.detect_feet(peak_frame)
        
        if not all([rim_y_takeoff, rim_y_peak, feet_y_takeoff, feet_y_peak]):
            return {'vertical_inches': None, 'confidence': 0, 'error': 'Could not detect rim or feet'}
        
        takeoff_distance_px = abs(rim_y_takeoff - feet_y_takeoff)
        peak_distance_px = abs(rim_y_peak - feet_y_peak)
        jump_px = takeoff_distance_px - peak_distance_px
        
        if jump_px <= 0:
            return {'vertical_inches': None, 'confidence': 0, 'error': 'Invalid jump measurement'}
        
        pixels_per_inch = takeoff_distance_px / self.RIM_HEIGHT_INCHES
        vertical_inches = jump_px / pixels_per_inch
        
        confidence = (rim_conf_takeoff + rim_conf_peak + feet_conf_takeoff + feet_conf_peak) / 4
        confidence = min(0.98, max(0.55, confidence)) * 100
        
        if vertical_inches < 10 or vertical_inches > 60:
            confidence *= 0.5
            
        return {
            'vertical_inches': round(vertical_inches, 1),
            'confidence': round(confidence),
            'error': None
        }
    
    # ============================================
    # SPRINT SPEED DETECTION
    # ============================================
    
    def detect_player_position(self, frame: np.ndarray) -> Tuple[Optional[int], float]:
        """Detect player's horizontal position (x-coordinate) for sprint tracking"""
        try:
            # Use motion detection or color-based tracking
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            # Find vertical strip where player is likely located
            vertical_projection = np.sum(edges, axis=0)
            
            # Find the peak in horizontal projection (where player is)
            height, width = frame.shape[:2]
            center_region = width // 4, 3 * width // 4
            
            best_x = None
            best_strength = 0
            
            for x in range(center_region[0], center_region[1]):
                if vertical_projection[x] > best_strength:
                    best_strength = vertical_projection[x]
                    best_x = x
            
            if best_x:
                confidence = min(0.9, best_strength / 500)
                return best_x, confidence
            return None, 0.0
        except Exception as e:
            return None, 0.0
    
    def estimate_distance_reference(self, frame: np.ndarray) -> Optional[float]:
        """Estimate distance reference from court markings (basketball court or football field)"""
        try:
            # Look for court lines or yard markers
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            # Detect horizontal lines (court boundaries)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
            
            if lines is not None:
                # Count significant horizontal lines
                horizontal_lines = 0
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if abs(y1 - y2) < 10:  # Horizontal line
                        horizontal_lines += 1
                
                # Estimate based on number of court lines visible
                if horizontal_lines >= 5:
                    return self.BASKETBALL_COURT_LENGTH_FT  # Full court
                elif horizontal_lines >= 3:
                    return self.BASKETBALL_HALF_COURT_FT  # Half court
            return None
        except Exception as e:
            return None
    
    def calculate_sprint(self, frames: list, fps: float) -> Dict:
        """Calculate 40-yard sprint time from video frames"""
        
        positions = []
        timestamps = []
        
        for i, frame in enumerate(frames):
            player_x, confidence = self.detect_player_position(frame)
            if player_x:
                positions.append(player_x)
                timestamps.append(i / fps)  # Time in seconds
        
        if len(positions) < 10:
            return {'sprint_seconds': None, 'confidence': 0, 'error': 'Not enough movement detected'}
        
        # Find start position (first significant movement after standing)
        start_idx = 0
        end_idx = len(positions) - 1
        
        # Calculate distance traveled in pixels
        start_pos = positions[start_idx]
        end_pos = positions[end_idx]
        distance_px = abs(end_pos - start_pos)
        
        # Estimate real distance (needs reference point)
        # For demo, use estimated court length
        estimated_distance_ft = self.estimate_distance_reference(frames[0])
        
        if estimated_distance_ft:
            # Convert pixels to feet
            pixels_per_foot = distance_px / estimated_distance_ft if distance_px > 0 else 1
            actual_distance_ft = self.SPRINT_DISTANCE_FEET
            time_seconds = timestamps[end_idx] - timestamps[start_idx]
            
            if time_seconds <= 0:
                return {'sprint_seconds': None, 'confidence': 0, 'error': 'Invalid time measurement'}
            
            # Adjust for actual distance
            if distance_px > 0:
                scale_factor = actual_distance_ft / estimated_distance_ft
                sprint_seconds = time_seconds * scale_factor
            else:
                sprint_seconds = time_seconds
            
            confidence = min(0.95, 0.7 + (distance_px / 500))
            
            return {
                'sprint_seconds': round(sprint_seconds, 2),
                'confidence': round(confidence * 100),
                'error': None
            }
        
        # Fallback: estimate based on frame count (less accurate)
        return {
            'sprint_seconds': None,
            'confidence': 0,
            'error': 'Could not detect distance reference (court lines or yard markers)'
        }
    
    # ============================================
    # MAIN ANALYSIS METHODS
    # ============================================
    
    def analyze_vertical(self, instagram_url: str, claimed_vertical: Optional[float] = None) -> Dict:
        """Analyze vertical leap from Instagram video"""
        result = {'success': False, 'vertical_inches': None, 'confidence': 0, 'error': None}
        
        video_path = self.download_instagram_video(instagram_url)
        if not video_path:
            result['error'] = 'Failed to download Instagram video'
            return result
        
        try:
            frames, _ = self.extract_frames(video_path, frame_interval=3)
            if len(frames) < 5:
                result['error'] = 'Video too short'
                return result
            
            takeoff_frame, peak_frame, _ = self.find_best_vertical_frames(frames)
            
            if takeoff_frame is None or peak_frame is None:
                result['error'] = 'Could not detect jump motion'
                return result
            
            calc_result = self.calculate_vertical(takeoff_frame, peak_frame)
            
            if calc_result.get('error') or calc_result['vertical_inches'] is None:
                result['error'] = calc_result.get('error', 'Could not calculate vertical')
                return result
            
            result['success'] = True
            result['vertical_inches'] = calc_result['vertical_inches']
            result['confidence'] = calc_result['confidence']
            
            return result
            
        except Exception as e:
            result['error'] = f'Analysis failed: {str(e)}'
            return result
        finally:
            if os.path.exists(video_path):
                os.unlink(video_path)
    
    def analyze_sprint(self, instagram_url: str, claimed_sprint: Optional[float] = None) -> Dict:
        """Analyze 40-yard sprint from Instagram video"""
        result = {'success': False, 'sprint_seconds': None, 'confidence': 0, 'error': None}
        
        video_path = self.download_instagram_video(instagram_url)
        if not video_path:
            result['error'] = 'Failed to download Instagram video'
            return result
        
        try:
            frames, fps = self.extract_frames(video_path, frame_interval=2)
            if len(frames) < 10:
                result['error'] = 'Video too short for sprint analysis'
                return result
            
            calc_result = self.calculate_sprint(frames, fps)
            
            if calc_result.get('error') or calc_result['sprint_seconds'] is None:
                result['error'] = calc_result.get('error', 'Could not calculate sprint time')
                return result
            
            result['success'] = True
            result['sprint_seconds'] = calc_result['sprint_seconds']
            result['confidence'] = calc_result['confidence']
            
            return result
            
        except Exception as e:
            result['error'] = f'Analysis failed: {str(e)}'
            return result
        finally:
            if os.path.exists(video_path):
                os.unlink(video_path)
    
    def analyze_both(self, instagram_url: str, claimed_vertical: Optional[float] = None, claimed_sprint: Optional[float] = None) -> Dict:
        """Analyze both vertical leap and sprint speed"""
        vertical_result = self.analyze_vertical(instagram_url, claimed_vertical)
        sprint_result = self.analyze_sprint(instagram_url, claimed_sprint)
        
        return {
            'vertical': vertical_result,
            'sprint': sprint_result
        }
