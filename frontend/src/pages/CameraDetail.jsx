import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export default function CameraDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const canvasRef = useRef(null)
  const [camera, setCamera] = useState(null)
  const [activeTab, setActiveTab] = useState('live')
  const [zones, setZones] = useState([])
  const [events, setEvents] = useState([])
  const [snapshot, setSnapshot] = useState(null)
  const [editing, setEditing] = useState(false)
  const [formData, setFormData] = useState({})
  const [saving, setSaving] = useState(false)
  
  // Zone drawing state
  const [drawing, setDrawing] = useState(false)
  const [currentPolygon, setCurrentPolygon] = useState([])
  const [imageSize, setImageSize] = useState({ width: 640, height: 480 })

  useEffect(() => {
    fetchCamera()
    fetchZones()
    fetchEvents()
  }, [id])

  useEffect(() => {
    if (activeTab === 'live') {
      const interval = setInterval(refreshSnapshot, 1000)
      return () => clearInterval(interval)
    }
    if (activeTab === 'zones') {
      refreshSnapshot()
    }
  }, [activeTab, id])

  const fetchCamera = async () => {
    const res = await fetch(`${API_URL}/api/cameras/${id}`)
    const data = await res.json()
    setCamera(data)
    setFormData({
      name: data.name,
      address: data.address || '',
      port: data.port || 554,
      username: '',
      password: ''
    })
  }

  const fetchZones = async () => {
    const res = await fetch(`${API_URL}/api/cameras/${id}/zones`)
    const data = await res.json()
    setZones(data)
  }

  const fetchEvents = async () => {
    const res = await fetch(`${API_URL}/api/events?camera_id=${id}&limit=20`)
    const data = await res.json()
    setEvents(data)
  }

  const refreshSnapshot = async () => {
    try {
      const res = await fetch(`${API_URL}/api/streams/cameras/${id}/snapshot`)
      if (res.ok) {
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        setSnapshot(url)
        
        // Get image dimensions
        const img = new Image()
        img.onload = () => {
          setImageSize({ width: img.width, height: img.height })
        }
        img.src = url
      }
    } catch (err) {}
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const res = await fetch(`${API_URL}/api/cameras/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      if (res.ok) {
        fetchCamera()
        setEditing(false)
      }
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (confirm('Delete this camera?')) {
      await fetch(`${API_URL}/api/cameras/${id}`, { method: 'DELETE' })
      navigate('/cameras')
    }
  }

  const handleTest = async () => {
    const res = await fetch(`${API_URL}/api/cameras/${id}/test`, { method: 'POST' })
    const data = await res.json()
    alert(data.connected ? 'Connected!' : 'Failed to connect')
  }

  // Zone drawing handlers
  const handleCanvasClick = (e) => {
    if (!drawing) return
    
    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const scaleX = imageSize.width / rect.width
    const scaleY = imageSize.height / rect.height
    
    const x = (e.clientX - rect.left) * scaleX / imageSize.width
    const y = (e.clientY - rect.top) * scaleY / imageSize.height
    
    setCurrentPolygon([...currentPolygon, { x, y }])
  }

  const finishPolygon = async () => {
    if (currentPolygon.length < 3) {
      alert('Need at least 3 points to create a zone')
      return
    }
    
    const name = prompt('Enter zone name:')
    if (!name) return
    
    const res = await fetch(`${API_URL}/api/cameras/${id}/zones`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, polygon: currentPolygon })
    })
    
    if (res.ok) {
      setDrawing(false)
      setCurrentPolygon([])
      fetchZones()
    }
  }

  const cancelDrawing = () => {
    setDrawing(false)
    setCurrentPolygon([])
  }

  const toggleZone = async (zoneId) => {
    await fetch(`${API_URL}/api/cameras/zones/${zoneId}/toggle`, { method: 'PATCH' })
    fetchZones()
  }

  const deleteZone = async (zoneId) => {
    if (!confirm('Delete this zone?')) return
    await fetch(`${API_URL}/api/cameras/zones/${zoneId}`, { method: 'DELETE' })
    fetchZones()
  }

  // Draw zones on canvas
  useEffect(() => {
    if (activeTab !== 'zones' || !snapshot) return
    
    const canvas = canvasRef.current
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')
    const img = new Image()
    img.onload = () => {
      canvas.width = img.width
      canvas.height = img.height
      ctx.drawImage(img, 0, 0)
      
      // Draw existing zones
      zones.forEach(zone => {
        if (zone.polygon && zone.polygon.length > 0) {
          ctx.beginPath()
          ctx.moveTo(zone.polygon[0].x * img.width, zone.polygon[0].y * img.height)
          for (let i = 1; i < zone.polygon.length; i++) {
            ctx.lineTo(zone.polygon[i].x * img.width, zone.polygon[i].y * img.height)
          }
          ctx.closePath()
          ctx.fillStyle = zone.enabled ? 'rgba(0, 255, 0, 0.3)' : 'rgba(128, 128, 128, 0.3)'
          ctx.fill()
          ctx.strokeStyle = zone.enabled ? '#4ade80' : '#666'
          ctx.lineWidth = 2
          ctx.stroke()
          
          // Draw label
          ctx.fillStyle = '#fff'
          ctx.font = '14px Arial'
          ctx.fillText(zone.name, zone.polygon[0].x * img.width + 5, zone.polygon[0].y * img.height - 5)
        }
      })
      
      // Draw current polygon being drawn
      if (currentPolygon.length > 0) {
        ctx.beginPath()
        ctx.moveTo(currentPolygon[0].x * img.width, currentPolygon[0].y * img.height)
        for (let i = 1; i < currentPolygon.length; i++) {
          ctx.lineTo(currentPolygon[i].x * img.width, currentPolygon[i].y * img.height)
        }
        ctx.strokeStyle = '#ff6b6b'
        ctx.lineWidth = 2
        ctx.setLineDash([5, 5])
        ctx.stroke()
        ctx.setLineDash([])
        
        // Draw points
        currentPolygon.forEach((point, i) => {
          ctx.beginPath()
          ctx.arc(point.x * img.width, point.y * img.height, 5, 0, Math.PI * 2)
          ctx.fillStyle = '#ff6b6b'
          ctx.fill()
        })
      }
    }
    img.src = snapshot
  }, [activeTab, snapshot, zones, currentPolygon])

  if (!camera) return <div>Loading...</div>

  return (
    <div className="camera-detail">
      <div className="detail-header">
        <button className="back-btn" onClick={() => navigate('/')}>← Back</button>
        <h2>{camera.name}</h2>
        <span className={`camera-type-badge ${camera.type.toLowerCase()}`}>{camera.type}</span>
      </div>

      <div className="detail-tabs">
        <button className={activeTab === 'live' ? 'active' : ''} onClick={() => setActiveTab('live')}>Live View</button>
        <button className={activeTab === 'playback' ? 'active' : ''} onClick={() => setActiveTab('playback')}>Playback</button>
        <button className={activeTab === 'settings' ? 'active' : ''} onClick={() => setActiveTab('settings')}>Settings</button>
        <button className={activeTab === 'zones' ? 'active' : ''} onClick={() => setActiveTab('zones')}>Detection Zones</button>
      </div>

      <div className="detail-content">
        {activeTab === 'live' && (
          <div className="live-view">
            {snapshot ? (
              <img src={snapshot} alt="Live feed" className="live-image" />
            ) : (
              <div className="live-loading">Loading...</div>
            )}
          </div>
        )}

        {activeTab === 'playback' && (
          <div className="playback-view">
            <h3>Recent Events</h3>
            {events.length === 0 ? (
              <p className="empty">No events recorded</p>
            ) : (
              <div className="event-list">
                {events.map(event => (
                  <div key={event.id} className="event-item">
                    <span className="event-type">{event.type}</span>
                    <span className="event-time">
                      {new Date(event.start_time).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="settings-view">
            <div className="settings-section">
              <h3>Camera Info</h3>
              {editing ? (
                <div className="edit-form">
                  <div className="form-group">
                    <label>Name</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={e => setFormData({...formData, name: e.target.value})}
                    />
                  </div>
                  <div className="form-group">
                    <label>Address</label>
                    <input
                      type="text"
                      value={formData.address}
                      onChange={e => setFormData({...formData, address: e.target.value})}
                    />
                  </div>
                  <div className="form-group">
                    <label>Port</label>
                    <input
                      type="number"
                      value={formData.port}
                      onChange={e => setFormData({...formData, port: parseInt(e.target.value)})}
                    />
                  </div>
                  <div className="form-group">
                    <label>Username (leave blank to keep current)</label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={e => setFormData({...formData, username: e.target.value})}
                    />
                  </div>
                  <div className="form-group">
                    <label>Password (leave blank to keep current)</label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={e => setFormData({...formData, password: e.target.value})}
                    />
                  </div>
                  <div className="form-actions">
                    <button onClick={() => setEditing(false)}>Cancel</button>
                    <button className="btn-primary" onClick={handleSave} disabled={saving}>
                      {saving ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="settings-display">
                  <div className="setting-row">
                    <span className="setting-label">Name</span>
                    <span className="setting-value">{camera.name}</span>
                  </div>
                  <div className="setting-row">
                    <span className="setting-label">Type</span>
                    <span className="setting-value">{camera.type}</span>
                  </div>
                  <div className="setting-row">
                    <span className="setting-label">Address</span>
                    <span className="setting-value">{camera.address || 'N/A'}</span>
                  </div>
                  <div className="setting-row">
                    <span className="setting-label">Port</span>
                    <span className="setting-value">{camera.port || 'N/A'}</span>
                  </div>
                  <div className="setting-row">
                    <span className="setting-label">Status</span>
                    <span className="setting-value">{camera.enabled ? 'Enabled' : 'Disabled'}</span>
                  </div>
                  <div className="setting-actions">
                    <button onClick={() => setEditing(true)}>Edit</button>
                    <button onClick={handleTest}>Test Connection</button>
                    <button onClick={handleDelete} className="btn-danger">Delete</button>
                  </div>
                </div>
              )}
            </div>

            <div className="settings-section">
              <h3>Recording Settings</h3>
              <div className="settings-display">
                <div className="setting-row">
                  <span className="setting-label">Continuous Recording</span>
                  <span className="setting-value">1 FPS (always on)</span>
                </div>
                <div className="setting-row">
                  <span className="setting-label">Event Recording</span>
                  <span className="setting-value">15 FPS (when triggered)</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'zones' && (
          <div className="zones-view">
            <div className="zones-toolbar">
              <h3>Detection Zones</h3>
              <div className="zone-buttons">
                {drawing ? (
                  <>
                    <button className="btn-primary" onClick={finishPolygon}>Finish Zone</button>
                    <button onClick={cancelDrawing}>Cancel</button>
                  </>
                ) : (
                  <button className="btn-primary" onClick={() => setDrawing(true)}>Draw New Zone</button>
                )}
              </div>
            </div>
            
            {drawing && (
              <div className="drawing-instructions">
                Click on the image to add points. Click "Finish Zone" when done (minimum 3 points).
              </div>
            )}
            
            <div className="zone-editor">
              {snapshot ? (
                <canvas
                  ref={canvasRef}
                  onClick={handleCanvasClick}
                  style={{ maxWidth: '100%', cursor: drawing ? 'crosshair' : 'default' }}
                />
              ) : (
                <div className="zone-loading">Loading camera preview...</div>
              )}
            </div>

            <div className="zone-list-section">
              <h4>Existing Zones</h4>
              {zones.length === 0 ? (
                <p className="empty">No detection zones configured</p>
              ) : (
                <div className="zone-list">
                  {zones.map(zone => (
                    <div key={zone.id} className="zone-item">
                      <div className="zone-info">
                        <span className="zone-name">{zone.name}</span>
                        <span className={`zone-status ${zone.enabled ? 'enabled' : 'disabled'}`}>
                          {zone.enabled ? 'Active' : 'Disabled'}
                        </span>
                      </div>
                      <div className="zone-actions">
                        <button onClick={() => toggleZone(zone.id)}>
                          {zone.enabled ? 'Disable' : 'Enable'}
                        </button>
                        <button onClick={() => deleteZone(zone.id)} className="btn-danger">Delete</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
