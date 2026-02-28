import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useCameras, useEvents, useRecordings } from '../hooks/useApi'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export default function Playback() {
  const [searchParams] = useSearchParams()
  const cameraIdFromUrl = searchParams.get('camera_id')
  
  const { cameras } = useCameras()
  const [selectedCamera, setSelectedCamera] = useState(cameraIdFromUrl || '')
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const { recordings } = useRecordings(selectedCamera, selectedDate)
  const { events } = useEvents(selectedCamera)
  const [selectedRecording, setSelectedRecording] = useState(null)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [playingEvent, setPlayingEvent] = useState(null)

  // Generate date options (last 14 days)
  const dates = []
  for (let i = 0; i < 14; i++) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    dates.push(d.toISOString().split('T')[0])
  }

  useEffect(() => {
    if (cameras.length > 0 && !selectedCamera) {
      setSelectedCamera(cameras[0].id)
    }
  }, [cameras])

  const selectedCameraName = cameras.find(c => c.id === selectedCamera)?.name || 'Unknown'

  return (
    <div className="playback-page">
      <h2>Playback</h2>

      <div className="playback-controls">
        <div className="control-group">
          <label>Camera</label>
          <select value={selectedCamera} onChange={e => setSelectedCamera(e.target.value)}>
            <option value="">All Cameras</option>
            {cameras.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div className="control-group">
          <label>Date</label>
          <select value={selectedDate} onChange={e => setSelectedDate(e.target.value)}>
            {dates.map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="playback-content">
        <div className="recordings-section">
          <h3>Continuous Recording</h3>
          {recordings.length === 0 ? (
            <p className="empty">No recording for {selectedDate}</p>
          ) : (
            <div className="recording-list">
              {recordings.map(rec => (
                <div
                  key={`${rec.camera_id}-${rec.date}`}
                  className={`recording-item ${selectedRecording === rec.path ? 'selected' : ''}`}
                  onClick={() => {
                    setSelectedRecording(rec.path)
                    setSelectedEvent(null)
                    setPlayingEvent(null)
                  }}
                >
                  <span className="rec-date">{rec.camera_name}</span>
                  <span className="rec-size">{Math.round(rec.size / 1024 / 1024)} MB</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="viewer-section">
          {playingEvent ? (
            <div className="video-container">
              <video controls autoPlay src={`${API_URL}/api/events/${playingEvent.id}/clip`}>
                Your browser does not support video.
              </video>
              <div className="video-info">
                <span className="event-badge">{playingEvent.type}</span>
                <span>{new Date(playingEvent.start_time).toLocaleString()}</span>
                <button onClick={() => setPlayingEvent(null)}>Close</button>
              </div>
            </div>
          ) : selectedRecording ? (
            <video controls src={`${API_URL}/api/recordings/${selectedCamera || cameras[0]?.id}/${selectedDate}`}>
              Your browser does not support video playback.
            </video>
          ) : selectedEvent ? (
            <div className="event-preview">
              {selectedEvent.thumbnail_path && (
                <img 
                  src={`${API_URL}/api/events/${selectedEvent.id}/thumbnail`} 
                  alt="Event thumbnail"
                />
              )}
              <div className="event-details">
                <h4>{selectedEvent.type}</h4>
                <p>{new Date(selectedEvent.start_time).toLocaleString()}</p>
                {selectedEvent.clip_path && (
                  <button 
                    className="btn-primary"
                    onClick={() => setPlayingEvent(selectedEvent)}
                  >
                    Play Clip
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="viewer-empty">
              <p>Select a recording or event to play</p>
            </div>
          )}
        </div>

        <div className="events-section">
          <h3>Events ({events.length})</h3>
          {events.length === 0 ? (
            <p className="empty">No events</p>
          ) : (
            <div className="event-list">
              {events.map(event => (
                <div 
                  key={event.id} 
                  className={`event-item ${selectedEvent?.id === event.id ? 'selected' : ''}`}
                  onClick={() => {
                    setSelectedEvent(event)
                    setSelectedRecording(null)
                  }}
                >
                  <span className="event-type">{event.type}</span>
                  <span className="event-time">
                    {new Date(event.start_time).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
