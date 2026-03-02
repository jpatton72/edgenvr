from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import cv2
import numpy as np
import threading
import io
import time

from app.models.database import Camera, get_db
from app.core.security import get_security_manager
from app.services.recorder import recorder_manager

router = APIRouter(prefix="/api/streams", tags=["streams"])
security = get_security_manager()

# MJPEG frame cache
frame_cache = {}
cache_lock = threading.Lock()


def generate_mjpeg(camera_id: str, db: Session):
    """Generate MJPEG stream for camera."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        return
    
    while True:
        # Use shared recorder to get frames
        ret, frame = recorder_manager.get_frame(camera_id)
        
        if not ret or frame is None:
            # Fallback: try opening directly
            stream_url = camera.address if camera.type == "USB" else camera.rtsp_url
            if not stream_url and camera.address:
                username = security.decrypt(camera.username) if camera.username else ""
                password = security.decrypt(camera.password) if camera.password else ""
                from app.services.camera_manager import RTSPHandler
                rtsp = RTSPHandler()
                stream_url = rtsp.build_url(
                    camera.address,
                    camera.port or 554,
                    username,
                    password
                )
            
            if stream_url:
                cap = cv2.VideoCapture(stream_url)
                ret, frame = cap.read()
                cap.release()
        
        if not ret or frame is None:
            time.sleep(1)
            continue
        
        # Cache latest frame
        with cache_lock:
            frame_cache[camera_id] = frame.copy()
        
        # Encode as JPEG
        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ret:
            continue
        
        frame_bytes = jpeg.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@router.get("/cameras/{camera_id}/stream")
def stream_camera(camera_id: str, db: Session = Depends(get_db)):
    """Get MJPEG live stream for camera."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return StreamingResponse(
        generate_mjpeg(camera_id, db),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/cameras/{camera_id}/snapshot")
def snapshot_camera(camera_id: str, db: Session = Depends(get_db)):
    """Get single snapshot from camera."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Try to get cached frame first
    with cache_lock:
        if camera_id in frame_cache:
            frame = frame_cache[camera_id]
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                return StreamingResponse(
                    io.BytesIO(jpeg.tobytes()),
                    media_type="image/jpeg"
                )
    
    # Use shared recorder (avoid opening camera multiple times)
    # The recorder already handles camera access - don't compete with it
    for attempt in range(3):
        ret, frame = recorder_manager.get_frame(camera_id)
        if ret and frame is not None:
            break
        time.sleep(0.5)  # Wait for recorder to get frame
    
    if not ret or frame is None:
        raise HTTPException(status_code=500, detail="Camera not available - recorder may not be running")
    
    ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to encode frame")
    
    return StreamingResponse(
        io.BytesIO(jpeg.tobytes()),
        media_type="image/jpeg"
    )
