import cv2
import numpy as np
import threading
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime

from app.core.config import get_settings

settings = get_settings()

# COCO person class ID
PERSON_CLASS_ID = 0


class YOLOAnalytics:
    """Edge AI analytics using YOLO for person detection."""
    
    def __init__(self, model_path: str = "yolo26n.pt"):
        """Initialize YOLO model."""
        import os
        import urllib.request
        
        # Download model if not exists
        if not os.path.exists(model_path):
            print(f"Downloading YOLO26n model...")
            # Try YOLO26n first, fall back to YOLOv8n
            try:
                url = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt"
                urllib.request.urlretrieve(url, model_path)
                print(f"YOLO26n model downloaded to {model_path}")
            except Exception as e:
                print(f"YOLO26n download failed: {e}, trying YOLOv8n...")
                model_path = "yolov8n.pt"
                if not os.path.exists(model_path):
                    url = "https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.pt"
                    urllib.request.urlretrieve(url, model_path)
                    print(f"YOLOv8n model downloaded")
        
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.model.to('cpu')  # Force CPU inference
            self.available = True
            print(f"YOLO model loaded: {model_path}")
        except Exception as e:
            print(f"YOLO init failed: {e}")
            self.model = None
            self.available = False
    
    def detect_persons(self, frame: np.ndarray, confidence: float = None) -> List[Dict]:
        """Detect persons in frame, return bounding boxes."""
        if not self.available or self.model is None:
            return []
        
        if confidence is None:
            confidence = settings.DETECTION_THRESHOLD
        
        try:
            results = self.model(frame, conf=confidence, verbose=False)
            persons = []
            
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    if int(box.cls[0]) == PERSON_CLASS_ID:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        persons.append({
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],
                            "confidence": float(box.conf[0])
                        })
            
            return persons
        except Exception as e:
            print(f"Detection error: {e}")
            return []


class ZoneDetector:
    """Check if detections intersect with defined zones."""
    
    @staticmethod
    def point_in_polygon(x: float, y: float, polygon: List[Dict]) -> bool:
        """Ray casting algorithm for point in polygon."""
        n = len(polygon)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]["x"], polygon[i]["y"]
            xj, yj = polygon[j]["x"], polygon[j]["y"]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside
    
    @staticmethod
    def bbox_intersects_zone(bbox: List[float], polygon: List[Dict]) -> bool:
        """Check if bounding box intersects with polygon zone."""
        x1, y1, x2, y2 = bbox
        
        # Check if any corner is in zone
        corners = [
            (x1, y1), (x1, y2), (x2, y1), (x2, y2),
            ((x1 + x2) / 2, (y1 + y2) / 2)  # Center point
        ]
        
        for x, y in corners:
            if ZoneDetector.point_in_polygon(x, y, polygon):
                return True
        
        return False


class AnalyticsEngine:
    """Main analytics processing engine."""
    
    def __init__(self):
        self.yolo = YOLOAnalytics()
        self.zone_detector = ZoneDetector()
        self.threads: Dict[str, threading.Thread] = {}
        self.running_cameras: Dict[str, bool] = {}
        self.enabled_zones: Dict[str, List[Dict]] = {}
        
        # Callbacks
        self.on_person_detected: Optional[Callable] = None
    
    def start_camera(self, camera_id: str, stream_url: str, zones: List[Dict]):
        """Start analytics processing for a camera."""
        if camera_id in self.threads:
            return
        
        self.enabled_zones[camera_id] = zones
        self.running_cameras[camera_id] = True
        
        thread = threading.Thread(
            target=self._process_loop,
            args=(camera_id, stream_url),
            daemon=True
        )
        thread.start()
        self.threads[camera_id] = thread
        print(f"Started analytics for camera {camera_id}")
    
    def stop_camera(self, camera_id: str):
        """Stop analytics for a camera."""
        self.running_cameras[camera_id] = False
        if camera_id in self.threads:
            del self.threads[camera_id]
        if camera_id in self.enabled_zones:
            del self.enabled_zones[camera_id]
        print(f"Stopped analytics for camera {camera_id}")
    
    def update_zones(self, camera_id: str, zones: List[Dict]):
        """Update detection zones for camera."""
        self.enabled_zones[camera_id] = zones
        print(f"Updated zones for camera {camera_id}: {len(zones)} zones")
    
    def _process_loop(self, camera_id: str, stream_url: str):
        """Main analytics processing loop."""
        print(f"Analytics loop starting for {camera_id} with URL: {stream_url}")
        cap = cv2.VideoCapture(stream_url)
        frame_count = 0
        last_detection_time = 0
        
        while self.running_cameras.get(camera_id, False):
            ret, frame = cap.read()
            if not ret:
                time.sleep(1)
                cap = cv2.VideoCapture(stream_url)
                continue
            
            # Process every Nth frame
            frame_count += 1
            if frame_count % settings.DETECTION_INTERVAL != 0:
                time.sleep(0.03)
                continue
            
            # Detect persons
            persons = self.yolo.detect_persons(frame)
            
            if persons:
                print(f"Camera {camera_id}: Detected {len(persons)} person(s)")
            
            # Get zones for this camera
            zones = self.enabled_zones.get(camera_id, [])
            
            # If no zones defined, detect persons anywhere in frame
            if not zones:
                if persons and self.on_person_detected:
                    # Rate limit: only trigger once per 10 seconds
                    current_time = time.time()
                    if current_time - last_detection_time > 10:
                        print(f"Camera {camera_id}: Person detected (no zones configured)")
                        self.on_person_detected(camera_id, persons[0])
                        last_detection_time = current_time
            else:
                # Check against zones
                for person in persons:
                    for zone in zones:
                        if zone.get("enabled", True):
                            if self.zone_detector.bbox_intersects_zone(
                                person["bbox"], 
                                zone["polygon"]
                            ):
                                # Person in zone - trigger event
                                current_time = time.time()
                                if current_time - last_detection_time > 10:
                                    print(f"Camera {camera_id}: Person in zone!")
                                    if self.on_person_detected:
                                        self.on_person_detected(camera_id, person)
                                    last_detection_time = current_time
                                break
            
            time.sleep(0.03)
        
        cap.release()
        print(f"Analytics loop ended for {camera_id}")


# Global instance
analytics_engine = AnalyticsEngine()
