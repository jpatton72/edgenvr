import cv2
import os
import time
import threading
from datetime import datetime
from typing import Dict, Optional
from collections import deque

from app.core.config import get_settings

settings = get_settings()


class CameraCapture:
    """Shared camera capture for a single camera - used by both recorder and analytics."""
    
    def __init__(self, camera_id: str, stream_url: str):
        self.camera_id = camera_id
        self.stream_url = stream_url
        self.cap: Optional[cv2.VideoCapture] = None
        self.lock = threading.Lock()
        self.running = True
        
        # Start capture thread
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
    
    def _capture_loop(self):
        """Continuous capture loop."""
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.stream_url)
                time.sleep(1)
                continue
            
            ret, frame = self.cap.read()
            if not ret:
                self.cap.release()
                self.cap = None
                time.sleep(1)
                continue
            
            time.sleep(0.03)  # ~30fps cap
    
    def read(self):
        """Get latest frame."""
        with self.lock:
            if self.cap and self.cap.isOpened():
                self.cap.grab()
                ret, frame = self.cap.retrieve()
                return ret, frame
            return False, None
    
    def get_fresh_frame(self):
        """Get a fresh frame (not cached)."""
        with self.lock:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                return ret, frame
            return False, None
    
    def is_available(self):
        """Check if camera is available."""
        with self.lock:
            return self.cap is not None and self.cap.isOpened()
    
    def stop(self):
        """Stop capture."""
        self.running = False
        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None


class RingBuffer:
    """In-memory ring buffer for pre-event recording."""
    
    def __init__(self, max_seconds: int = 30, fps: int = 1):
        self.max_frames = max_seconds * fps
        self.buffer = deque(maxlen=self.max_frames)
        self.fps = fps
    
    def add_frame(self, frame):
        self.buffer.append(frame)
    
    def get_frames(self):
        return list(self.buffer)
    
    def clear(self):
        self.buffer.clear()


class VideoRecorder:
    """Handle continuous and event-based video recording."""
    
    def __init__(self, camera_id: str, stream_url: str):
        self.camera_id = camera_id
        self.stream_url = stream_url
        self.running = False
        self.thread = None
        
        # Shared camera capture
        self.camera_capture: Optional[CameraCapture] = None
        
        # Recording state
        self.is_recording_event = False
        self.event_buffer = RingBuffer(
            settings.PRE_BUFFER_SECONDS, 
            settings.CONTINUOUS_FPS
        )
        
        # Callbacks
        self.on_event_triggered: Optional[Callable] = None
        self.on_event_ended: Optional[Callable] = None
        
        # Paths
        self.recordings_dir = os.path.join(settings.RECORDINGS_PATH, camera_id)
        self.events_dir = os.path.join(settings.EVENTS_PATH, camera_id)
        os.makedirs(self.recordings_dir, exist_ok=True)
        os.makedirs(self.events_dir, exist_ok=True)
    
    def start(self):
        """Start the recording thread."""
        self.running = True
        # Start shared camera capture
        self.camera_capture = CameraCapture(self.camera_id, self.stream_url)
        self.thread = threading.Thread(target=self._record_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop recording."""
        self.running = False
        if self.camera_capture:
            self.camera_capture.stop()
        if self.thread:
            self.thread.join(timeout=5)
    
    def get_frame(self):
        """Get current frame from shared capture."""
        if self.camera_capture:
            return self.camera_capture.read()
        return False, None
    
    def is_available(self):
        """Check if camera is available."""
        if self.camera_capture and self.camera_capture.cap:
            return self.camera_capture.cap.isOpened()
        return False
    
    def _record_loop(self):
        """Main recording loop."""
        current_date = None
        continuous_writer = None
        
        while self.running:
            ret, frame = self.get_frame()
            if not ret or frame is None:
                time.sleep(1)
                continue
            
            timestamp = datetime.now()
            date_str = timestamp.strftime("%Y-%m-%d")
            
            # Pre-buffer for events
            self.event_buffer.add_frame(frame.copy())
            
            # Continuous recording (1 FPS)
            if date_str != current_date:
                if continuous_writer:
                    continuous_writer.release()
                current_date = date_str
                output_path = os.path.join(self.recordings_dir, f"{date_str}.mp4")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                continuous_writer = cv2.VideoWriter(
                    output_path, fourcc, settings.CONTINUOUS_FPS,
                    (frame.shape[1], frame.shape[0])
                )
            
            if continuous_writer and timestamp.second == 0:
                continuous_writer.write(frame)
            
            # Event recording handled by analytics service
            time.sleep(1 / settings.CONTINUOUS_FPS)
        
        if continuous_writer:
            continuous_writer.release()
    
    def trigger_event(self):
        """Start high-FPS event recording."""
        if not self.is_recording_event:
            self.is_recording_event = True
            threading.Thread(
                target=self._record_event_clip,
                args=(self.event_buffer.get_frames(),),
                daemon=True
            ).start()
    
    def _record_event_clip(self, pre_buffer_frames):
        """Record event clip with pre-buffer and post-buffer."""
        timestamp = datetime.now()
        output_path = os.path.join(
            self.events_dir, 
            f"event_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        h, w = pre_buffer_frames[0].shape[:2] if pre_buffer_frames else (480, 640)
        writer = cv2.VideoWriter(output_path, fourcc, settings.EVENT_FPS, (w, h))
        
        # Write pre-buffer frames (upsampled to 15 FPS)
        for frame in pre_buffer_frames:
            for _ in range(settings.EVENT_FPS // settings.CONTINUOUS_FPS):
                writer.write(frame)
        
        # Record post-buffer using shared capture
        post_frames = settings.POST_BUFFER_SECONDS * settings.EVENT_FPS
        
        for _ in range(post_frames):
            ret, frame = self.get_frame()
            if ret and frame is not None:
                writer.write(frame)
            time.sleep(1 / settings.EVENT_FPS)
        
        if writer:
            writer.release()
        
        # Generate thumbnail
        thumbnail_path = None
        if pre_buffer_frames:
            thumbnail_path = output_path.replace('.mp4', '_thumb.jpg')
            cv2.imwrite(thumbnail_path, pre_buffer_frames[-1])
        
        self.is_recording_event = False
        
        # Callback for event created
        if self.on_event_ended:
            self.on_event_ended(output_path, thumbnail_path)


class RecorderManager:
    """Manage recorders for all cameras."""
    
    def __init__(self):
        self.recorders: Dict[str, VideoRecorder] = {}
    
    def add_camera(self, camera_id: str, stream_url: str):
        """Add camera and start recording."""
        if camera_id not in self.recorders:
            recorder = VideoRecorder(camera_id, stream_url)
            recorder.start()
            self.recorders[camera_id] = recorder
    
    def remove_camera(self, camera_id: str):
        """Stop and remove camera recorder."""
        if camera_id in self.recorders:
            self.recorders[camera_id].stop()
            del self.recorders[camera_id]
    
    def trigger_event(self, camera_id: str):
        """Trigger event recording for camera."""
        if camera_id in self.recorders:
            self.recorders[camera_id].trigger_event()
    
    def get_frame(self, camera_id: str):
        """Get current frame for camera."""
        if camera_id in self.recorders:
            return self.recorders[camera_id].get_frame()
        return False, None


# Global instance
recorder_manager = RecorderManager()
