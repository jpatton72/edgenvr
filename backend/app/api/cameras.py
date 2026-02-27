from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.models.database import Camera, Zone, Event, get_db
from app.services.camera_manager import CameraManager
from app.services.recorder import recorder_manager
from app.services.analytics import analytics_engine
from app.core.security import get_security_manager

router = APIRouter(prefix="/api/cameras", tags=["cameras"])
camera_manager = CameraManager()
security = get_security_manager()


# Pydantic models
class CameraCreate(BaseModel):
    name: str
    type: str  # ONVIF, USB, RTSP
    address: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    rtsp_url: Optional[str] = None


class CameraResponse(BaseModel):
    id: str
    name: str
    type: str
    address: Optional[str]
    port: Optional[int]
    enabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ZoneCreate(BaseModel):
    name: str
    polygon: List[dict]  # [{"x": 0.1, "y": 0.1}, ...]


class ZoneResponse(BaseModel):
    id: str
    camera_id: str
    name: str
    polygon: List[dict]
    enabled: bool


@router.post("/discover", response_model=List[dict])
def discover_cameras():
    """Discover ONVIF and USB cameras on the network."""
    return camera_manager.discover_all()


@router.get("", response_model=List[CameraResponse])
def list_cameras(db: Session = Depends(get_db)):
    """List all configured cameras."""
    cameras = db.query(Camera).all()
    return cameras


@router.post("", response_model=CameraResponse)
def create_camera(camera: CameraCreate, db: Session = Depends(get_db)):
    """Add a new camera."""
    # Encrypt credentials
    enc_username = security.encrypt(camera.username) if camera.username else None
    enc_password = security.encrypt(camera.password) if camera.password else None
    
    # Build stream URL
    stream_url = camera.rtsp_url
    if not stream_url and camera.type == "RTSP" and camera.address:
        from app.services.camera_manager import RTSPHandler
        rtsp = RTSPHandler()
        stream_url = rtsp.build_url(
            camera.address, 
            camera.port or 554, 
            camera.username or "", 
            camera.password or "",
            "/stream"
        )
    
    db_camera = Camera(
        name=camera.name,
        type=camera.type,
        address=camera.address,
        port=camera.port,
        username=enc_username,
        password=enc_password,
        rtsp_url=stream_url
    )
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    
    # Start recorder and analytics
    if stream_url:
        recorder_manager.add_camera(db_camera.id, stream_url)
        zones = db.query(Zone).filter(Zone.camera_id == db_camera.id, Zone.enabled == True).all()
        analytics_engine.start_camera(
            db_camera.id, 
            stream_url, 
            [{"polygon": z.polygon, "enabled": z.enabled} for z in zones]
        )
    
    return db_camera


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: str, db: Session = Depends(get_db)):
    """Get camera details."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.delete("/{camera_id}")
def delete_camera(camera_id: str, db: Session = Depends(get_db)):
    """Remove a camera."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Stop recorder and analytics
    recorder_manager.remove_camera(camera_id)
    analytics_engine.stop_camera(camera_id)
    
    db.delete(camera)
    db.commit()
    
    return {"status": "deleted"}


@router.post("/{camera_id}/test")
def test_camera(camera_id: str, db: Session = Depends(get_db)):
    """Test camera connection."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    from app.services.camera_manager import RTSPHandler
    rtsp = RTSPHandler()
    
    # Decrypt credentials
    username = security.decrypt(camera.username) if camera.username else ""
    password = security.decrypt(camera.password) if camera.password else ""
    
    test_url = camera.rtsp_url or rtsp.build_url(
        camera.address, camera.port or 554, username, password
    )
    
    result = rtsp.test_connection(test_url)
    
    return {"connected": result}


# Zone endpoints
@router.get("/{camera_id}/zones", response_model=List[ZoneResponse])
def list_zones(camera_id: str, db: Session = Depends(get_db)):
    """List detection zones for camera."""
    zones = db.query(Zone).filter(Zone.camera_id == camera_id).all()
    return zones


@router.post("/{camera_id}/zones", response_model=ZoneResponse)
def create_zone(camera_id: str, zone: ZoneCreate, db: Session = Depends(get_db)):
    """Create detection zone for camera."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    db_zone = Zone(
        camera_id=camera_id,
        name=zone.name,
        polygon=zone.polygon
    )
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)
    
    # Update analytics engine
    zones = db.query(Zone).filter(Zone.camera_id == camera_id, Zone.enabled == True).all()
    analytics_engine.update_zones(
        camera_id, 
        [{"polygon": z.polygon, "enabled": z.enabled} for z in zones]
    )
    
    return db_zone


@router.put("/zones/{zone_id}", response_model=ZoneResponse)
def update_zone(zone_id: str, zone: ZoneCreate, db: Session = Depends(get_db)):
    """Update detection zone."""
    db_zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not db_zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    db_zone.name = zone.name
    db_zone.polygon = zone.polygon
    db.commit()
    db.refresh(db_zone)
    
    # Update analytics
    zones = db.query(Zone).filter(Zone.camera_id == db_zone.camera_id, Zone.enabled == True).all()
    analytics_engine.update_zones(
        db_zone.camera_id,
        [{"polygon": z.polygon, "enabled": z.enabled} for z in zones]
    )
    
    return db_zone


@router.delete("/zones/{zone_id}")
def delete_zone(zone_id: str, db: Session = Depends(get_db)):
    """Delete detection zone."""
    db_zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not db_zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    camera_id = db_zone.camera_id
    db.delete(db_zone)
    db.commit()
    
    # Update analytics
    zones = db.query(Zone).filter(Zone.camera_id == camera_id, Zone.enabled == True).all()
    analytics_engine.update_zones(
        camera_id,
        [{"polygon": z.polygon, "enabled": z.enabled} for z in zones]
    )
    
    return {"status": "deleted"}
