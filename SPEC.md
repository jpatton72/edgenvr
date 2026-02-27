# EdgeNVR - Specification Document

## 1. Project Overview

**Project Name:** EdgeNVR  
**Type:** Self-hosted Network Video Recorder with Edge AI Analytics  
**Core Functionality:** Auto-discover and manage ONVIF/USB/RTSP cameras, continuous low-FPS recording with high-FPS event triggers, local video analytics for person detection in definable zones.  
**Target Users:** Home and small business security deployments  
**Max Cameras:** 8 (expandable)

---

## 2. Technical Architecture

### 2.1 Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Language | Python 3.11+ | Best ONVIF, FFmpeg bindings, ML libraries |
| Web Server | FastAPI + uvicorn | Async I/O, auto-generated docs, lightweight |
| Frontend | React + Vite | Modern UI, easy state management |
| Database | SQLite | Zero-config, sufficient for metadata |
| Video Processing | FFmpeg + OpenCV | Industry standard |
| Analytics | Ultralytics YOLO26 | Latest edge-optimized, NMS-free |
| Container | Docker Compose | Easy deployment |

### 2.2 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        EdgeNVR Server                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  ONVIF       │  │  USB         │  │  RTSP                │ │
│  │  Discovery   │  │  Detection   │  │  Manual Input        │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │
│         │                  │                      │              │
│         └──────────────────┼──────────────────────┘              │
│                            ▼                                      │
│                 ┌─────────────────────┐                          │
│                 │   Camera Manager    │                          │
│                 │   (unified interface)│                          │
│                 └──────────┬──────────┘                          │
│                            │                                      │
│         ┌──────────────────┼──────────────────┐                  │
│         ▼                  ▼                  ▼                  │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐            │
│  │ Live Grid   │   │ Recording   │   │ Analytics   │            │
│  │ (Web UI)    │   │ Engine      │   │ Engine      │            │
│  │             │   │ (1/15 FPS)  │   │ (YOLO26)    │            │
│  └─────────────┘   └─────────────┘   └─────────────┘            │
│                            │                  │                    │
│                            ▼                  ▼                  │
│                 ┌─────────────────────┐   ┌─────────────┐       │
│                 │   Storage Layer     │   │ Event       │       │
│                 │   (recordings)      │   │ Triggers    │       │
│                 └─────────────────────┘   └─────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Functional Requirements

### 3.1 Camera Discovery & Management

#### ONVIF Discovery
- **Auto-discovery**: Broadcast UDP probe on port 3702
- **Parse**: Extract device info, profiles, stream URLs
- **Authentication**: Support WS-UsernameToken auth
- **Manual add**: Enter IP, port, username, password if auto-discovery fails

#### USB Camera Detection
- **Auto-detect**: Enumerate `/dev/video*` devices
- **Info**: Capture device name, capabilities via V4L2
- **Hot-plug**: Monitor for USB connect/disconnect events

#### RTSP Streams
- **Manual input**: URL format `rtsp://user:pass@ip:port/path`
- **Credential storage**: Encrypted at rest
- **Connection testing**: Verify stream before saving

### 3.2 Video Recording

#### Continuous Recording (1 FPS)
- **Format**: H.264/MP4, 1 FPS, ~100KB/minute
- **Storage**: Organized by `cameras/<camera_id>/YYYY-MM-DD.mp4`
- **Retention**: Configurable (default 7 days)
- **Playback**: Accessible via web UI, scrubbing support

#### Event Recording (15 FPS)
- **Trigger**: Person detected in configured zone
- **Duration**: Pre-buffer (5s) + event + post-buffer (10s)
- **Format**: H.264/MP4, 15 FPS, ~15MB/minute
- **Storage**: `events/<camera_id>/<timestamp>.mp4`
- **Retention**: Separate from continuous (default 30 days)

#### Pre/Post Buffer
- **Implementation**: Ring buffer in memory (30 seconds)
- **On event**: Flush ring buffer to disk + continue at high FPS

### 3.3 Video Analytics

#### Person Detection
- **Model**: YOLO26n (nano - latest edge-optimized, ~6MB)
- **Processing**: Every 5th frame of live stream (reduces load)
- **Output**: Bounding boxes, confidence scores, timestamps
- **Update mechanism**: Model file can be swapped for newer versions

#### Zone Definition
- **UI**: Draw polygons on camera view
- **Storage**: Saved per camera in database
- **Logic**: Trigger when person bounding box intersects zone

#### Event Types
- `person_detected` - Person in zone
- `person_left` - Person exited zone
- `motion_detected` - Significant frame difference (fallback)

### 3.4 Web Interface

#### Dashboard
- **Grid view**: 1x1 to 4x4 camera layout
- **Live streams**: Low-latency via MJPEG or WebRTC
- **Status indicators**: Online/offline/recording/event
- **Click to expand**: Single camera full-screen

#### Camera Management
- **List**: All discovered/configured cameras
- **Add**: Auto-discovered or manual entry
- **Edit**: Credentials, name, location
- **Delete**: Remove with confirmation
- **Test**: Verify connection before saving

#### Playback
- **Timeline**: Calendar-based date selection
- **Scrubbing**: Seek through recording
- **Download**: Export clip to local machine
- **Events**: Jump to event timestamps

#### Analytics Settings
- **Zone editor**: Draw detection zones overlay
- **Sensitivity**: Adjust detection threshold
- **Notifications**: (Future) webhook/push options

---

## 4. Security Requirements

### 4.1 Authentication
- **Web UI**: Session-based auth with bcrypt password hashing
- **Default credentials**: Force change on first login
- **Camera credentials**: AES-256 encrypted at rest
- **API**: Token-based for external integrations

### 4.2 Network
- **Defaults**: Bind to localhost only (127.0.0.1)
- **TLS**: Optional self-signed cert support
- **Rate limiting**: On API endpoints

### 4.3 System
- **Permissions**: Run as non-root user (docker volume mounts)
- **Updates**: Signed model files only
- **Logs**: No credential leakage in logs

---

## 5. Deployment

### 5.1 Quick Start
```bash
git clone https://github.com/your-repo/edgenvr.git
cd edgenvr
cp .env.example .env
docker compose up -d
# Access UI at http://localhost:8080
```

### 5.2 Directory Structure
```
edgenvr/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── core/         # Config, security
│   │   ├── models/       # Database models
│   │   ├── services/     # Business logic
│   │   └── utils/        # Helpers
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── hooks/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

### 5.3 Environment Variables
```
# Server
HOST=0.0.0.0
PORT=8080
SECRET_KEY=<generate-random>

# Storage
RECORDINGS_PATH=/data/recordings
RETENTION_DAYS=7

# Analytics
ANALYTICS_MODEL=yolov8n.pt
DETECTION_THRESHOLD=0.5
```

---

## 6. Data Models

### Camera
```
id: UUID
name: String
type: Enum(ONVIF, USB, RTSP)
address: String (IP/URL)
port: Int
username: String (encrypted)
password: String (encrypted)
rtsp_url: String (optional)
enabled: Boolean
created_at: DateTime
```

### Zone
```
id: UUID
camera_id: UUID (FK)
name: String
polygon: JSON (array of {x, y} points)
enabled: Boolean
```

### Event
```
id: UUID
camera_id: UUID (FK)
type: Enum(person_detected, person_left, motion)
start_time: DateTime
end_time: DateTime (nullable)
clip_path: String (nullable)
thumbnail_path: String
```

---

## 7. API Endpoints

### Cameras
- `GET /api/cameras` - List all cameras
- `POST /api/cameras/discover` - Trigger ONVIF discovery
- `POST /api/cameras` - Add camera
- `GET /api/cameras/{id}` - Get camera details
- `PUT /api/cameras/{id}` - Update camera
- `DELETE /api/cameras/{id}` - Remove camera
- `POST /api/cameras/{id}/test` - Test connection

### Streams
- `GET /api/cameras/{id}/stream` - Live MJPEG stream
- `GET /api/cameras/{id}/snapshot` - Single frame

### Recording
- `GET /api/recordings` - List recordings by date
- `GET /api/recordings/{id}/download` - Download clip
- `GET /api/events` - List events
- `GET /api/events/{id}/clip` - Get event clip

### Analytics
- `GET /api/cameras/{id}/zones` - List zones
- `POST /api/cameras/{id}/zones` - Create zone
- `PUT /api/zones/{id}` - Update zone
- `DELETE /api/zones/{id}` - Remove zone

### System
- `GET /api/health` - Health check
- `GET /api/stats` - Storage, recording stats

---

## 8. Acceptance Criteria

### Must Have (MVP)
- [ ] ONVIF camera discovery works
- [ ] Can add camera manually (RTSP)
- [ ] Live view shows video in grid
- [ ] 1 FPS continuous recording works
- [ ] 15 FPS event recording triggers on person detection
- [ ] Web UI accessible and functional
- [ ] Recordings are playable from UI
- [ ] Deploys via docker-compose

### Should Have
- [ ] USB camera detection
- [ ] Zone drawing in UI
- [ ] Pre/post buffer implementation
- [ ] Event playback with timeline

### Nice to Have
- [ ] Mobile-friendly UI
- [ ] Multi-user support
- [ ] Remote clip transmission
- [ ] Mobile push notifications

---

## 9. Future Considerations

- [ ] Multiple detection models (vehicle, animal, face)
- [ ] Integration with home automation (Home Assistant)
- [ ] Cloud backup option
- [ ] AI summarization of footage
- [ ] License plate recognition module

---

*Spec Version: 1.0*  
*Created: 2026-02-27*
