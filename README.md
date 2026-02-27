# EdgeNVR

Self-hosted Network Video Recorder with Edge AI Analytics.

## Features

- **Auto-discovery**: ONVIF camera detection, USB camera support, manual RTSP
- **Continuous Recording**: 1 FPS to local storage
- **Event Recording**: 15 FPS triggered by person detection
- **Edge Analytics**: YOLO26n person detection in configurable zones
- **Web UI**: Live grid, playback, camera management

## Quick Start

```bash
# Clone and setup
cp .env.example .env

# Start with Docker
docker compose up -d

# Access UI
http://localhost:8080
```

## Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Configuration

Edit `.env` to customize:
- Storage paths
- Detection threshold
- Recording FPS
- Buffer durations

## API

- `GET /api/cameras` - List cameras
- `POST /api/cameras/discover` - Discover ONVIF/USB cameras
- `POST /api/cameras` - Add camera
- `GET /api/cameras/{id}/stream` - Live MJPEG stream
- `GET /api/recordings` - List recordings
- `GET /api/events` - List events

## Architecture

```
Backend: FastAPI + SQLite
Frontend: React + Vite
Analytics: YOLO26n (local, no cloud)
Storage: Local filesystem
```
