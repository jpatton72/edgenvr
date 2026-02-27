from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import os

from app.models.database import Event, get_db
from app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["recordings"])
settings = get_settings()


class EventResponse(BaseModel):
    id: str
    camera_id: str
    type: str
    start_time: datetime
    end_time: Optional[datetime]
    clip_path: Optional[str]
    thumbnail_path: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/recordings")
def list_recordings(
    camera_id: Optional[str] = None,
    date: Optional[str] = None,  # YYYY-MM-DD
    db: Session = Depends(get_db)
):
    """List available recordings."""
    from app.models.database import Camera
    
    recordings = []
    
    if camera_id:
        cameras = [db.query(Camera).filter(Camera.id == camera_id).first()]
    else:
        cameras = db.query(Camera).all()
    
    for camera in cameras:
        if not camera:
            continue
        recordings_dir = os.path.join(settings.RECORDINGS_PATH, camera.id)
        if not os.path.exists(recordings_dir):
            continue
        
        for filename in os.listdir(recordings_dir):
            if filename.endswith('.mp4'):
                filepath = os.path.join(recordings_dir, filename)
                file_date = filename.replace('.mp4', '')
                
                if date and file_date != date:
                    continue
                
                recordings.append({
                    "camera_id": camera.id,
                    "camera_name": camera.name,
                    "date": file_date,
                    "path": filepath,
                    "size": os.path.getsize(filepath)
                })
    
    return sorted(recordings, key=lambda x: x["date"], reverse=True)


@router.get("/recordings/{camera_id}/{date}")
def get_recording(camera_id: str, date: str, db: Session = Depends(get_db)):
    """Get recording file for camera on specific date."""
    filepath = os.path.join(settings.RECORDINGS_PATH, camera_id, f"{date}.mp4")
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Recording not found")
    
    return FileResponse(
        filepath,
        media_type="video/mp4",
        filename=f"{camera_id}_{date}.mp4"
    )


@router.get("/events", response_model=List[EventResponse])
def list_events(
    camera_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List recorded events."""
    query = db.query(Event)
    
    if camera_id:
        query = query.filter(Event.camera_id == camera_id)
    
    events = query.order_by(Event.start_time.desc()).limit(limit).all()
    return events


@router.get("/events/{event_id}", response_model=EventResponse)
def get_event(event_id: str, db: Session = Depends(get_db)):
    """Get event details."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/events/{event_id}/clip")
def get_event_clip(event_id: str, db: Session = Depends(get_db)):
    """Download event video clip."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event or not event.clip_path:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    if not os.path.exists(event.clip_path):
        raise HTTPException(status_code=404, detail="Clip file not found")
    
    return FileResponse(
        event.clip_path,
        media_type="video/mp4",
        filename=f"event_{event_id}.mp4"
    )


@router.get("/events/{event_id}/thumbnail")
def get_event_thumbnail(event_id: str, db: Session = Depends(get_db)):
    """Get event thumbnail."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event or not event.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    if not os.path.exists(event.thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    return FileResponse(
        event.thumbnail_path,
        media_type="image/jpeg"
    )


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get system statistics."""
    from app.models.database import Camera
    
    cameras = db.query(Camera).all()
    events = db.query(Event).filter(Event.start_time >= datetime.utcnow() - timedelta(days=1)).all()
    
    # Calculate storage
    total_size = 0
    recordings_count = 0
    
    for camera in cameras:
        rec_dir = os.path.join(settings.RECORDINGS_PATH, camera.id)
        evt_dir = os.path.join(settings.EVENTS_PATH, camera.id)
        
        for d in [rec_dir, evt_dir]:
            if os.path.exists(d):
                for root, dirs, files in os.walk(d):
                    for f in files:
                        total_size += os.path.getsize(os.path.join(root, f))
                        recordings_count += 1
    
    return {
        "cameras": {
            "total": len(cameras),
            "enabled": len([c for c in cameras if c.enabled])
        },
        "events_today": len(events),
        "storage": {
            "used_bytes": total_size,
            "recordings_count": recordings_count
        }
    }
