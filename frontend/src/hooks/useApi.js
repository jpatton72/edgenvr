import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export function useCameras() {
  const [cameras, setCameras] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchCameras = async () => {
    try {
      const res = await fetch(`${API_URL}/api/cameras`)
      const data = await res.json()
      setCameras(data)
    } catch (err) {
      console.error('Failed to fetch cameras:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCameras()
  }, [])

  const discover = async () => {
    const res = await fetch(`${API_URL}/api/cameras/discover`, { method: 'POST' })
    return await res.json()
  }

  const addCamera = async (camera) => {
    const res = await fetch(`${API_URL}/api/cameras`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(camera)
    })
    await fetchCameras()
    return await res.json()
  }

  const deleteCamera = async (id) => {
    await fetch(`${API_URL}/api/cameras/${id}`, { method: 'DELETE' })
    await fetchCameras()
  }

  const testCamera = async (id) => {
    const res = await fetch(`${API_URL}/api/cameras/${id}/test`, { method: 'POST' })
    return await res.json()
  }

  return { cameras, loading, fetchCameras, discover, addCamera, deleteCamera, testCamera }
}

export function useStream(cameraId) {
  const [snapshot, setSnapshot] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!cameraId) return

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/api/streams/cameras/${cameraId}/snapshot`)
        if (res.ok) {
          const blob = await res.blob()
          setSnapshot(URL.createObjectURL(blob))
        }
      } catch (err) {
        setError(err.message)
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [cameraId])

  return { snapshot, error }
}

export function useEvents(cameraId) {
  const [events, setEvents] = useState([])

  const fetchEvents = async () => {
    const url = cameraId 
      ? `${API_URL}/api/events?camera_id=${cameraId}`
      : `${API_URL}/api/events`
    const res = await fetch(url)
    const data = await res.json()
    setEvents(data)
  }

  useEffect(() => {
    fetchEvents()
  }, [cameraId])

  return { events, fetchEvents }
}

export function useRecordings(cameraId, date) {
  const [recordings, setRecordings] = useState([])

  const fetchRecordings = async () => {
    let url = `${API_URL}/api/recordings`
    const params = new URLSearchParams()
    if (cameraId) params.append('camera_id', cameraId)
    if (date) params.append('date', date)
    if (params.toString()) url += '?' + params.toString()
    
    const res = await fetch(url)
    const data = await res.json()
    setRecordings(data)
  }

  useEffect(() => {
    fetchRecordings()
  }, [cameraId, date])

  return { recordings, fetchRecordings }
}
