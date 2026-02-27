import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export default function Settings() {
  const [stats, setStats] = useState(null)
  const [zones, setZones] = useState({})
  const [showZoneModal, setShowZoneModal] = useState(false)
  const [selectedCamera, setSelectedCamera] = useState('')

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/stats`)
      const data = await res.json()
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const formatBytes = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB'
    return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB'
  }

  return (
    <div className="settings-page">
      <h2>Settings</h2>

      <div className="settings-section">
        <h3>System Status</h3>
        {stats ? (
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-value">{stats.cameras.total}</span>
              <span className="stat-label">Total Cameras</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.cameras.enabled}</span>
              <span className="stat-label">Enabled</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.events_today}</span>
              <span className="stat-label">Events Today</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{formatBytes(stats.storage.used_bytes)}</span>
              <span className="stat-label">Storage Used</span>
            </div>
          </div>
        ) : (
          <p>Loading stats...</p>
        )}
      </div>

      <div className="settings-section">
        <h3>Detection Zones</h3>
        <p className="section-desc">
          Define areas within camera views where person detection triggers event recording.
        </p>
        
        <div className="zone-info">
          <p>Select a camera to manage its detection zones.</p>
          <a href="/cameras">Go to Cameras →</a>
        </div>
      </div>

      <div className="settings-section">
        <h3>Recording Settings</h3>
        <div className="settings-list">
          <div className="setting-item">
            <span className="setting-label">Continuous Recording</span>
            <span className="setting-value">1 FPS (always on)</span>
          </div>
          <div className="setting-item">
            <span className="setting-label">Event Recording</span>
            <span className="setting-value">15 FPS (when triggered)</span>
          </div>
          <div className="setting-item">
            <span className="setting-label">Pre-Event Buffer</span>
            <span className="setting-value">5 seconds</span>
          </div>
          <div className="setting-item">
            <span className="setting-label">Post-Event Buffer</span>
            <span className="setting-value">10 seconds</span>
          </div>
        </div>
      </div>

      <div className="settings-section">
        <h3>Analytics</h3>
        <div className="settings-list">
          <div className="setting-item">
            <span className="setting-label">Detection Model</span>
            <span className="setting-value">YOLO26n (edge-optimized)</span>
          </div>
          <div className="setting-item">
            <span className="setting-label">Processing</span>
            <span className="setting-value">Every 5th frame</span>
          </div>
          <div className="setting-item">
            <span className="setting-label">Detection Classes</span>
            <span className="setting-value">Person (COCO class 0)</span>
          </div>
        </div>
      </div>
    </div>
  )
}
