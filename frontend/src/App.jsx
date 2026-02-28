import React from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Cameras from './pages/Cameras'
import Playback from './pages/Playback'
import Settings from './pages/Settings'
import CameraDetail from './pages/CameraDetail'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="sidebar">
          <h1>EdgeNVR</h1>
          <ul>
            <li><Link to="/">Dashboard</Link></li>
            <li><Link to="/cameras">Cameras</Link></li>
            <li><Link to="/playback">Playback</Link></li>
            <li><Link to="/settings">Settings</Link></li>
          </ul>
        </nav>
        <main className="content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/cameras" element={<Cameras />} />
            <Route path="/playback" element={<Playback />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/camera/:id" element={<CameraDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
