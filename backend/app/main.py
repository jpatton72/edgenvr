from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api import cameras, recordings, streams
from app.core.config import get_settings
from app.services.recorder import recorder_manager
from app.services.analytics import analytics_engine

settings = get_settings()

app = FastAPI(
    title="EdgeNVR API",
    description="Self-hosted Network Video Recorder with Edge AI",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Connect analytics events to recorder
def on_person_detected(camera_id: str, detection: dict):
    """Trigger event recording when person detected in zone."""
    recorder_manager.trigger_event(camera_id)
    
    # Create event in database
    from app.models.database import Event, SessionLocal
    db = SessionLocal()
    try:
        event = Event(
            camera_id=camera_id,
            type="person_detected"
        )
        db.add(event)
        db.commit()
    finally:
        db.close()


analytics_engine.on_person_detected = on_person_detected


# Include routers
app.include_router(cameras.router)
app.include_router(recordings.router)
app.include_router(streams.router)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "analytics": analytics_engine.yolo.available if analytics_engine else False
    }


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    os.makedirs(settings.RECORDINGS_PATH, exist_ok=True)
    os.makedirs(settings.EVENTS_PATH, exist_ok=True)
    
    # Load existing cameras
    from app.models.database import Camera, SessionLocal, Zone
    db = SessionLocal()
    try:
        cameras = db.query(Camera).filter(Camera.enabled == True).all()
        for camera in cameras:
            # Get stream URL based on camera type
            if camera.type == "USB":
                stream_url = camera.address  # e.g., /dev/video0
            else:
                stream_url = camera.rtsp_url
            
            if stream_url:
                # Start recorder
                recorder_manager.add_camera(camera.id, stream_url)
                
                # Load zones and start analytics
                zones = db.query(Zone).filter(
                    Zone.camera_id == camera.id,
                    Zone.enabled == True
                ).all()
                analytics_engine.start_camera(
                    camera.id,
                    stream_url,
                    [{"polygon": z.polygon, "enabled": z.enabled} for z in zones]
                )
                print(f"Started analytics for camera {camera.name} ({camera.type}): {stream_url}")
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    for camera_id in list(recorder_manager.recorders.keys()):
        recorder_manager.remove_camera(camera_id)
    
    for camera_id in list(analytics_engine.threads.keys()):
        analytics_engine.stop_camera(camera_id)
