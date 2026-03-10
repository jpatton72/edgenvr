import { useState, useEffect, useRef } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export default function PresenceDetection() {
  const [status, setStatus] = useState({ connected: false, source: null, clients: 0 })
  const [zones, setZones] = useState([])
  const [nodes, setNodes] = useState([])
  const [floorplan, setFloorplan] = useState(null)
  const [activeTab, setActiveTab] = useState('zones')
  const [sensingData, setSensingData] = useState(null)
  const [showZoneModal, setShowZoneModal] = useState(false)
  const [editingZone, setEditingZone] = useState(null)
  const [newZone, setNewZone] = useState({
    name: '',
    type: 'area',
    detection: 'presence',
    enabled: true,
    color: '#ff0000',
    coordinates: { x: 10, y: 10, width: 100, height: 100 }
  })
  
  const canvasRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    fetchStatus()
    fetchZones()
    fetchNodes()
    fetchFloorplan()
    
    // Poll for sensing data
    const interval = setInterval(fetchSensingData, 2000)
    return () => clearInterval(interval)
  }, [])

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/api/densepose/status`)
      const data = await res.json()
      setStatus(data)
    } catch (err) {
      setStatus({ connected: false })
    }
  }

  const fetchSensingData = async () => {
    try {
      const res = await fetch(`${API_URL}/api/densepose/sensing`)
      const data = await res.json()
      if (!data.error) {
        setSensingData(data)
      }
    } catch (err) {
      // Silently fail - DensePose may not be running
    }
  }

  const fetchZones = async () => {
    try {
      const res = await fetch(`${API_URL}/api/densepose/zones`)
      const data = await res.json()
      setZones(data)
    } catch (err) {
      console.error('Failed to fetch zones:', err)
    }
  }

  const fetchNodes = async () => {
    try {
      const res = await fetch(`${API_URL}/api/densepose/nodes`)
      const data = await res.json()
      setNodes(data)
    } catch (err) {
      console.error('Failed to fetch nodes:', err)
    }
  }

  const fetchFloorplan = async () => {
    try {
      const res = await fetch(`${API_URL}/api/densepose/floorplan`)
      if (res.ok) {
        const data = await res.json()
        setFloorplan(data)
      }
    } catch (err) {
      console.error('Failed to fetch floorplan:', err)
    }
  }

  const handleFloorPlanUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = async (event) => {
      const imageUrl = event.target.result
      
      // Get image dimensions
      const img = new Image()
      img.onload = async () => {
        const floorplanData = {
          image_url: imageUrl,
          width: img.width,
          height: img.height,
          scale: 1.0
        }
        
        await fetch(`${API_URL}/api/densepose/floorplan`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(floorplanData)
        })
        
        setFloorplan(floorplanData)
      }
      img.src = imageUrl
    }
    reader.readAsDataURL(file)
  }

  const handleSaveZone = async () => {
    const zone = {
      ...newZone,
      id: editingZone?.id || `zone-${Date.now()}`
    }

    const method = editingZone ? 'PUT' : 'POST'
    const url = editingZone 
      ? `${API_URL}/api/densepose/zones/${zone.id}`
      : `${API_URL}/api/densepose/zones`

    await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(zone)
    })

    fetchZones()
    setShowZoneModal(false)
    setEditingZone(null)
    setNewZone({
      name: '',
      type: 'area',
      detection: 'presence',
      enabled: true,
      color: '#ff0000',
      coordinates: { x: 10, y: 10, width: 100, height: 100 }
    })
  }

  const handleDeleteZone = async (zoneId) => {
    await fetch(`${API_URL}/api/densepose/zones/${zoneId}`, { method: 'DELETE' })
    fetchZones()
  }

  const testAlert = async () => {
    await fetch(`${API_URL}/api/densepose/alerts/test`, { method: 'POST' })
  }

  // Draw floor plan with zones
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')
    const width = floorplan?.width || 600
    const height = floorplan?.height || 400
    
    canvas.width = width
    canvas.height = height
    
    // Clear
    ctx.fillStyle = '#1a1a2e'
    ctx.fillRect(0, 0, width, height)
    
    // Draw floor plan image
    if (floorplan?.image_url) {
      const img = new Image()
      img.onload = () => {
        ctx.drawImage(img, 0, 0, width, height)
        drawZones(ctx, width, height)
      }
      img.src = floorplan.image_url
    } else {
      // Draw grid placeholder
      ctx.strokeStyle = '#333'
      ctx.lineWidth = 1
      for (let x = 0; x < width; x += 50) {
        ctx.beginPath()
        ctx.moveTo(x, 0)
        ctx.lineTo(x, height)
        ctx.stroke()
      }
      for (let y = 0; y < height; y += 50) {
        ctx.beginPath()
        ctx.moveTo(0, y)
        ctx.lineTo(width, y)
        ctx.stroke()
      }
      
      // Draw zones on placeholder
      drawZones(ctx, width, height)
    }
  }, [floorplan, zones])

  const drawZones = (ctx, width, height) => {
    zones.forEach(zone => {
      const { x, y, width: w, height: h } = zone.coordinates
      
      ctx.fillStyle = zone.color + '40'
      ctx.strokeStyle = zone.color
      ctx.lineWidth = 2
      ctx.fillRect(x, y, w, h)
      ctx.strokeRect(x, y, w, h)
      
      // Zone label
      ctx.fillStyle = '#fff'
      ctx.font = '12px sans-serif'
      ctx.fillText(zone.name, x + 5, y + 15)
    })
    
    // Draw nodes
    nodes.forEach(node => {
      const { x, y } = node.position
      ctx.beginPath()
      ctx.arc(x, y, 8, 0, Math.PI * 2)
      ctx.fillStyle = node.status === 'online' ? '#00ff00' : '#ff0000'
      ctx.fill()
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 2
      ctx.stroke()
    })
  }

  return (
    <div className="presence-detection-page">
      <div className="page-header">
        <h2>Presence Detection</h2>
        <div className={`status-badge ${status.connected ? 'connected' : 'disconnected'}`}>
          {status.connected ? '● Connected' : '○ Disconnected'}
          {status.source && <span className="source">{status.source}</span>}
        </div>
      </div>

      <div className="presence-layout">
        {/* Left Column: Floor Plan */}
        <div className="floor-plan-section">
          <div className="floor-plan-header">
            <h3>Floor Plan</h3>
            <div className="floor-plan-actions">
              <button onClick={() => fileInputRef.current?.click()}>
                Upload Image
              </button>
              {floorplan && (
                <button onClick={() => {
                  fetch(`${API_URL}/api/densepose/floorplan`, { method: 'DELETE' })
                  setFloorplan(null)
                }}>
                  Clear
                </button>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFloorPlanUpload}
                style={{ display: 'none' }}
              />
            </div>
          </div>
          
          <div className="canvas-container">
            <canvas ref={canvasRef} />
            {zones.length === 0 && !floorplan && (
              <div className="canvas-placeholder">
                Upload a floor plan or draw zones
              </div>
            )}
          </div>
          
          {/* Mode Selector */}
          <div className="mode-selector">
            <label>
              <input type="radio" name="mode" value="zones" defaultChecked />
              Zones
            </label>
            <label>
              <input type="radio" name="mode" value="heatmap" disabled />
              Heatmap (need 1+ nodes)
            </label>
            <label>
              <input type="radio" name="mode" value="triangulation" disabled />
              Triangulation (need 3+ nodes)
            </label>
          </div>
          
          {/* Sensing Status */}
          {status.connected && sensingData && (
            <div className="sensing-status">
              <h4>Live Status</h4>
              <div className="status-grid">
                <div className="status-item">
                  <span className="label">Motion</span>
                  <span className="value">{sensingData.motion_detected ? 'Detected' : 'None'}</span>
                </div>
                <div className="status-item">
                  <span className="label">Signal</span>
                  <span className="value">{sensingData.signal_strength?.toFixed(1) || 'N/A'} dB</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Configuration */}
        <div className="config-section">
          <div className="tabs">
            <button 
              className={activeTab === 'zones' ? 'active' : ''}
              onClick={() => setActiveTab('zones')}
            >
              Zones
            </button>
            <button 
              className={activeTab === 'nodes' ? 'active' : ''}
              onClick={() => setActiveTab('nodes')}
            >
              Nodes
            </button>
            <button 
              className={activeTab === 'alerts' ? 'active' : ''}
              onClick={() => setActiveTab('alerts')}
            >
              Alerts
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'zones' && (
              <div className="zones-tab">
                <button className="add-btn" onClick={() => setShowZoneModal(true)}>
                  + Add Zone
                </button>
                
                <div className="zones-list">
                  {zones.map(zone => (
                    <div key={zone.id} className="zone-item">
                      <div className="zone-info">
                        <span className="zone-name" style={{ color: zone.color }}>
                          {zone.name}
                        </span>
                        <span className="zone-type">{zone.type} / {zone.detection}</span>
                      </div>
                      <div className="zone-actions">
                        <button onClick={() => {
                          setEditingZone(zone)
                          setNewZone(zone)
                          setShowZoneModal(true)
                        }}>Edit</button>
                        <button onClick={() => handleDeleteZone(zone.id)}>Delete</button>
                      </div>
                    </div>
                  ))}
                  {zones.length === 0 && (
                    <p className="empty-state">No zones configured</p>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'nodes' && (
              <div className="nodes-tab">
                <p className="info-text">
                  Nodes will be auto-detected when ESP32 devices connect to the network.
                </p>
                <div className="nodes-list">
                  {nodes.map(node => (
                    <div key={node.id} className="node-item">
                      <span className="node-name">{node.name}</span>
                      <span className="node-ip">{node.ip}</span>
                      <span className={`node-status ${node.status}`}>
                        {node.status}
                      </span>
                    </div>
                  ))}
                  {nodes.length === 0 && (
                    <p className="empty-state">
                      No nodes detected. Connect ESP32 devices and ensure DensePose is running.
                    </p>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'alerts' && (
              <div className="alerts-tab">
                <button className="test-btn" onClick={testAlert}>
                  Send Test Alert
                </button>
                <p className="info-text">
                  Alerts will be sent via Telegram when presence is detected in configured zones.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Zone Modal */}
      {showZoneModal && (
        <div className="modal-overlay" onClick={() => setShowZoneModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>{editingZone ? 'Edit Zone' : 'Add Zone'}</h3>
            
            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                value={newZone.name}
                onChange={e => setNewZone({ ...newZone, name: e.target.value })}
                placeholder="e.g., Front Door"
              />
            </div>
            
            <div className="form-group">
              <label>Type</label>
              <select
                value={newZone.type}
                onChange={e => setNewZone({ ...newZone, type: e.target.value })}
              >
                <option value="entry">Entry</option>
                <option value="window">Window</option>
                <option value="area">Area</option>
                <option value="perimeter">Perimeter</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Detection</label>
              <select
                value={newZone.detection}
                onChange={e => setNewZone({ ...newZone, detection: e.target.value })}
              >
                <option value="presence">Presence</option>
                <option value="motion">Motion</option>
                <option value="fall">Fall</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Color</label>
              <input
                type="color"
                value={newZone.color}
                onChange={e => setNewZone({ ...newZone, color: e.target.value })}
              />
            </div>
            
            <div className="form-group">
              <label>Coordinates</label>
              <div className="coords-grid">
                <input
                  type="number"
                  placeholder="X"
                  value={newZone.coordinates.x}
                  onChange={e => setNewZone({ 
                    ...newZone, 
                    coordinates: { ...newZone.coordinates, x: parseInt(e.target.value) }
                  })}
                />
                <input
                  type="number"
                  placeholder="Y"
                  value={newZone.coordinates.y}
                  onChange={e => setNewZone({ 
                    ...newZone, 
                    coordinates: { ...newZone.coordinates, y: parseInt(e.target.value) }
                  })}
                />
                <input
                  type="number"
                  placeholder="Width"
                  value={newZone.coordinates.width}
                  onChange={e => setNewZone({ 
                    ...newZone, 
                    coordinates: { ...newZone.coordinates, width: parseInt(e.target.value) }
                  })}
                />
                <input
                  type="number"
                  placeholder="Height"
                  value={newZone.coordinates.height}
                  onChange={e => setNewZone({ 
                    ...newZone, 
                    coordinates: { ...newZone.coordinates, height: parseInt(e.target.value) }
                  })}
                />
              </div>
            </div>
            
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={newZone.notify_telegram}
                  onChange={e => setNewZone({ ...newZone, notify_telegram: e.target.checked })}
                />
                Send Telegram alerts
              </label>
            </div>
            
            <div className="modal-actions">
              <button onClick={() => setShowZoneModal(false)}>Cancel</button>
              <button className="primary" onClick={handleSaveZone}>
                {editingZone ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
