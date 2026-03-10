from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import httpx

router = APIRouter(prefix="/api/densepose", tags=["densepose"])

# DensePose container URL
DENSEPOSE_URL = os.environ.get("DENSEPOSE_URL", "http://localhost:3002")

# Local storage for zones and nodes
DATA_DIR = "/home/jean-galt/.edgenvr-densepose"
ZONES_FILE = os.path.join(DATA_DIR, "zones.json")
NODES_FILE = os.path.join(DATA_DIR, "nodes.json")
FLOORPLAN_FILE = os.path.join(DATA_DIR, "floorplan.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

os.makedirs(DATA_DIR, exist_ok=True)


# Models
class Zone(BaseModel):
    id: str
    name: str
    type: str  # entry, window, area, perimeter
    detection: str  # presence, motion, fall
    enabled: bool = True
    color: str = "#ff0000"
    coordinates: dict  # {x, y, width, height}
    camera_id: Optional[str] = None
    notify_telegram: bool = True


class DensePoseNode(BaseModel):
    id: int
    ip: str
    name: str
    position: dict  # {x, y}
    status: str = "online"


class FloorPlan(BaseModel):
    image_url: str
    width: int
    height: int
    scale: float = 1.0


class DensePoseSettings(BaseModel):
    enabled: bool = True
    camera_fusion_enabled: bool = False
    alert_threshold: float = 0.5


# Helper functions
def load_zones() -> List[Zone]:
    if os.path.exists(ZONES_FILE):
        with open(ZONES_FILE, "r") as f:
            data = json.load(f)
            return [Zone(**z) for z in data]
    return []


def save_zones(zones: List[Zone]):
    with open(ZONES_FILE, "w") as f:
        json.dump([z.model_dump() for z in zones], f)


def load_nodes() -> List[DensePoseNode]:
    if os.path.exists(NODES_FILE):
        with open(NODES_FILE, "r") as f:
            data = json.load(f)
            return [DensePoseNode(**n) for n in data]
    return []


def save_nodes(nodes: List[DensePoseNode]):
    with open(NODES_FILE, "w") as f:
        json.dump([n.model_dump() for n in nodes], f)


def load_floorplan() -> Optional[FloorPlan]:
    if os.path.exists(FLOORPLAN_FILE):
        with open(FLOORPLAN_FILE, "r") as f:
            return FloorPlan(**json.load(f))
    return None


def save_floorplan(floorplan: FloorPlan):
    with open(FLOORPLAN_FILE, "w") as f:
        json.dump(floorplan.model_dump(), f)


def load_settings() -> DensePoseSettings:
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return DensePoseSettings(**json.load(f))
    return DensePoseSettings()


def save_settings(settings: DensePoseSettings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings.model_dump(), f)


# DensePose Status
@router.get("/status")
async def get_status():
    """Get connection status to DensePose container."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DENSEPOSE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return {
                    "connected": True,
                    "status": data.get("status"),
                    "source": data.get("source"),
                    "clients": data.get("clients")
                }
    except Exception as e:
        pass
    
    return {
        "connected": False,
        "status": "disconnected",
        "source": None,
        "clients": 0
    }


@router.get("/sensing")
async def get_sensing_data():
    """Get latest sensing data from DensePose."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DENSEPOSE_URL}/api/v1/sensing/latest", timeout=5.0)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        pass
    return {"error": "Unable to connect to DensePose"}


@router.get("/pose")
async def get_pose():
    """Get latest pose data."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DENSEPOSE_URL}/api/v1/pose/current", timeout=5.0)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        pass
    return {"persons": []}


@router.get("/vital-signs")
async def get_vital_signs():
    """Get vital signs."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DENSEPOSE_URL}/api/v1/vital-signs", timeout=5.0)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        pass
    return {}


# Zones
@router.get("/zones")
def get_zones():
    """List all zones."""
    return load_zones()


@router.post("/zones")
def create_zone(zone: Zone):
    """Create a new zone."""
    zones = load_zones()
    zones.append(zone)
    save_zones(zones)
    return {"status": "success", "zone": zone}


@router.put("/zones/{zone_id}")
def update_zone(zone_id: str, zone: Zone):
    """Update a zone."""
    zones = load_zones()
    for i, z in enumerate(zones):
        if z.id == zone_id:
            zones[i] = zone
            save_zones(zones)
            return {"status": "success", "zone": zone}
    raise HTTPException(status_code=404, detail="Zone not found")


@router.delete("/zones/{zone_id}")
def delete_zone(zone_id: str):
    """Delete a zone."""
    zones = load_zones()
    zones = [z for z in zones if z.id != zone_id]
    save_zones(zones)
    return {"status": "success"}


# Nodes
@router.get("/nodes")
def get_nodes():
    """List all nodes."""
    return load_nodes()


@router.post("/nodes")
def create_node(node: DensePoseNode):
    """Add a new node."""
    nodes = load_nodes()
    nodes.append(node)
    save_nodes(nodes)
    return {"status": "success", "node": node}


@router.put("/nodes/{node_id}")
def update_node(node_id: int, node: DensePoseNode):
    """Update a node."""
    nodes = load_nodes()
    for i, n in enumerate(nodes):
        if n.id == node_id:
            nodes[i] = node
            save_nodes(nodes)
            return {"status": "success", "node": node}
    raise HTTPException(status_code=404, detail="Node not found")


@router.delete("/nodes/{node_id}")
def delete_node(node_id: int):
    """Delete a node."""
    nodes = load_nodes()
    nodes = [n for n in nodes if n.id != node_id]
    save_nodes(nodes)
    return {"status": "success"}


# Floor Plan
@router.get("/floorplan")
def get_floorplan():
    """Get current floor plan."""
    floorplan = load_floorplan()
    if floorplan:
        return floorplan
    return None


@router.post("/floorplan")
def upload_floorplan(floorplan: FloorPlan):
    """Upload floor plan."""
    save_floorplan(floorplan)
    return {"status": "success", "floorplan": floorplan}


@router.delete("/floorplan")
def delete_floorplan():
    """Delete floor plan."""
    if os.path.exists(FLOORPLAN_FILE):
        os.remove(FLOORPLAN_FILE)
    return {"status": "success"}


# Settings
@router.get("/settings")
def get_settings_endpoint():
    """Get DensePose settings."""
    return load_settings()


@router.post("/settings")
def update_settings(settings: DensePoseSettings):
    """Update DensePose settings."""
    save_settings(settings)
    return {"status": "success", "settings": settings}


# Alerts
@router.get("/alerts")
def get_alerts():
    """Get alert history."""
    alerts_file = os.path.join(DATA_DIR, "alerts.json")
    if os.path.exists(alerts_file):
        with open(alerts_file, "r") as f:
            return json.load(f)
    return []


@router.post("/alerts/test")
def test_alert():
    """Send a test alert."""
    from app.services.notifications import notification_service
    success = notification_service.send_telegram(
        "🔔 Test alert from Presence Detection\n"
        "WiFi DensePose integration is working!"
    )
    return {"status": "success" if success else "failed"}
