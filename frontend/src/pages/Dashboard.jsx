import { useState, useEffect } from 'react'
import { useCameras, useStream } from '../hooks/useApi'

function CameraCard({ camera }) {
  const { snapshot, error } = useStream(camera.id)

  return (
    <div className="camera-card">
      <div className="camera-preview">
        {error ? (
          <div className="camera-error">Offline</div>
        ) : snapshot ? (
          <img src={snapshot} alt={camera.name} />
        ) : (
          <div className="camera-loading">Loading...</div>
        )}
        <div className="camera-status">
          <span className={`status-dot ${camera.enabled ? 'online' : 'offline'}`}></span>
          {camera.name}
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { cameras, loading } = useCameras()
  const [gridSize, setGridSize] = useState(4)

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Live View</h2>
        <div className="grid-controls">
          <button onClick={() => setGridSize(1)} className={gridSize === 1 ? 'active' : ''}>1×1</button>
          <button onClick={() => setGridSize(2)} className={gridSize === 2 ? 'active' : ''}>2×2</button>
          <button onClick={() => setGridSize(4)} className={gridSize === 4 ? 'active' : ''}>4×4</button>
        </div>
      </div>

      {loading ? (
        <p>Loading cameras...</p>
      ) : cameras.length === 0 ? (
        <div className="empty-state">
          <p>No cameras configured</p>
          <a href="/cameras">Add cameras →</a>
        </div>
      ) : (
        <div className={`camera-grid grid-${gridSize}`}>
          {cameras.map(camera => (
            <CameraCard key={camera.id} camera={camera} />
          ))}
        </div>
      )}
    </div>
  )
}
