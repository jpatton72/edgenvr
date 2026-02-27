import { useState } from 'react'
import { useCameras } from '../hooks/useApi'

export default function Cameras() {
  const { cameras, discover, addCamera, deleteCamera, testCamera } = useCameras()
  const [showAdd, setShowAdd] = useState(false)
  const [discovered, setDiscovered] = useState([])
  const [form, setForm] = useState({
    name: '',
    type: 'RTSP',
    address: '',
    port: 554,
    username: '',
    password: '',
    rtsp_url: ''
  })
  const [testing, setTesting] = useState(null)

  const handleDiscover = async () => {
    const devices = await discover()
    setDiscovered(devices)
  }

  const handleAdd = async (e) => {
    e.preventDefault()
    await addCamera(form)
    setShowAdd(false)
    setForm({ name: '', type: 'RTSP', address: '', port: 554, username: '', password: '', rtsp_url: '' })
  }

  const handleTest = async (id) => {
    setTesting(id)
    const result = await testCamera(id)
    alert(result.connected ? 'Camera connected!' : 'Connection failed')
    setTesting(null)
  }

  const useDiscovered = (device) => {
    setForm({
      ...form,
      name: device.name || device.address,
      type: device.type,
      address: device.address,
      port: device.port || 554
    })
    setShowAdd(true)
  }

  return (
    <div className="cameras-page">
      <div className="page-header">
        <h2>Cameras</h2>
        <div className="header-actions">
          <button onClick={handleDiscover} className="btn-secondary">Discover</button>
          <button onClick={() => setShowAdd(true)} className="btn-primary">Add Camera</button>
        </div>
      </div>

      {discovered.length > 0 && (
        <div className="discovered-panel">
          <h3>Discovered Devices</h3>
          <div className="discovered-list">
            {discovered.map((d, i) => (
              <div key={i} className="discovered-item">
                <span>{d.type} - {d.address}</span>
                <button onClick={() => useDiscovered(d)}>Use</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {cameras.length === 0 ? (
        <div className="empty-state">
          <p>No cameras configured yet</p>
        </div>
      ) : (
        <div className="camera-list">
          {cameras.map(camera => (
            <div key={camera.id} className="camera-item">
              <div className="camera-info">
                <h4>{camera.name}</h4>
                <span className="camera-type">{camera.type}</span>
                <span className="camera-address">{camera.address}</span>
              </div>
              <div className="camera-actions">
                <button onClick={() => handleTest(camera.id)} disabled={testing === camera.id}>
                  {testing === camera.id ? 'Testing...' : 'Test'}
                </button>
                <button onClick={() => deleteCamera(camera.id)} className="btn-danger">Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <div className="modal-overlay" onClick={() => setShowAdd(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Add Camera</h3>
            <form onSubmit={handleAdd}>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Type</label>
                <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}>
                  <option value="RTSP">RTSP</option>
                  <option value="ONVIF">ONVIF</option>
                  <option value="USB">USB</option>
                </select>
              </div>
              {form.type !== 'USB' && (
                <>
                  <div className="form-group">
                    <label>Address (IP)</label>
                    <input
                      type="text"
                      value={form.address}
                      onChange={e => setForm({ ...form, address: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Port</label>
                    <input
                      type="number"
                      value={form.port}
                      onChange={e => setForm({ ...form, port: parseInt(e.target.value) })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Username</label>
                    <input
                      type="text"
                      value={form.username}
                      onChange={e => setForm({ ...form, username: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Password</label>
                    <input
                      type="password"
                      value={form.password}
                      onChange={e => setForm({ ...form, password: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>RTSP URL (optional)</label>
                    <input
                      type="text"
                      value={form.rtsp_url}
                      onChange={e => setForm({ ...form, rtsp_url: e.target.value })}
                      placeholder="rtsp://user:pass@ip:port/stream"
                    />
                  </div>
                </>
              )}
              <div className="form-actions">
                <button type="button" onClick={() => setShowAdd(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Add Camera</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
