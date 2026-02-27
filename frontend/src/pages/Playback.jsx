import { useState, useEffect } from 'react'
import { useCameras, useEvents, useRecordings } from '../hooks/useApi'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export default function Playback() {
  const { cameras } = useCameras()
  const [selectedCamera, setSelectedCamera] = useState('')
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const { recordings } = useRecordings(selectedCamera, selectedDate)
  const { events, fetchEvents } = useEvents(selectedCamera)
  const [selectedRecording, setSelectedRecording] = useState(null)

  // Generate date options (last 7 days)
  const dates = []
  for (let i = 0; i < 7; i++) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    dates.push(d.toISOString().split('T')[0])
  }

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
          <h3>Continuous Recordings</h3>
          {recordings.length === 0 ? (
            <p className="empty">No recordings for this date</p>
          ) : (
            <div className="recording-list">
              {recordings.map(rec => (
                <div
                  key={`${rec.camera_id}-${rec.date}`}
                  className={`recording-item ${selectedRecording === rec.path ? 'selected' : ''}`}
                  onClick={() => setSelectedRecording(rec.path)}
                >
                  <span className="rec-date">{rec.date}</span>
                  <span className="rec-camera">{rec.camera_name}</span>
                  <span className="rec-size">{Math.round(rec.size / 1024 / 1024)} MB</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="viewer-section">
          {selectedRecording ? (
            <video controls src={`${API_URL}/api/recordings/${selectedCamera || cameras[0]?.id}/${selectedDate}`}>
              Your browser does not support video playback.
            </video>
          ) : (
            <div className="viewer-empty">
              <p>Select a recording to play</p>
            </div>
          )}
        </div>

        <div className="events-section">
          <h3>Events</h3>
          {events.length === 0 ? (
            <p className="empty">No events</p>
          ) : (
            <div className="event-list">
              {events.map(event => (
                <div key={event.id} className="event-item">
                  <span className="event-type">{event.type}</span>
                  <span className="event-time">
                    {new Date(event.start_time).toLocaleTimeString()}
                  </span>
                  {event.thumbnail_path && (
                    <img 
                      src={`${API_URL}/api/events/${event.id}/thumbnail`} 
                      alt="Event"
                      className="event-thumb"
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
