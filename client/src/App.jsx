import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import './phase2.css'
import './App.css'
import './features/content/content.css'
import Navbar from './components/Navbar.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import { useAuth } from './context/AuthContext.js'
import EditProfile from './pages/EditProfile.jsx'
import FollowList from './pages/FollowList.jsx'
import Login from './pages/Login.jsx'
import Profile from './pages/Profile.jsx'
import Register from './pages/Register.jsx'
import { FeedPage } from './features/content/FeedPage.jsx'
import { ModerationPage } from './features/content/ModerationPage.jsx'

function NotFound() {
  return <p>Page not found.</p>
}

function Home() {
  const { loading } = useAuth()
  if (loading) return <p className="wl-muted">Loading…</p>
  return (
    <>
      <header className="app-header">
        <p className="eyebrow">WanderLog</p>
        <h1>WanderLog</h1>
        <p className="description">
          A text-only social media platform for travelers and wanderers.
        </p>
      </header>
      <FeedPage />
    </>
  )
}

function SystemStatus() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')
  const [showStatus, setShowStatus] = useState(false)

  useEffect(() => {
    let active = true
    fetch('/api/health')
      .then((response) => {
        if (!response.ok) throw new Error(`API returned HTTP ${response.status}`)
        return response.json()
      })
      .then((data) => {
        if (active) {
          setHealth(data)
          setError('')
        }
      })
      .catch((requestError) => {
        if (active) {
          setHealth(null)
          setError(requestError.message)
        }
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <footer className="api-footer">
      <button
        type="button"
        className="btn-status-toggle"
        onClick={() => setShowStatus((prev) => !prev)}
      >
        {showStatus ? '▲ Hide System Status' : '▼ System Status'}
      </button>
      {showStatus && (
        <section className="api-card" aria-live="polite">
          <h2>Backend status</h2>
          {health && <p className="status status-connected">Connected — {health.service}</p>}
          {error && <p className="status status-error">Could not connect to the backend: {error}</p>}
          {!health && !error && <p className="status">Checking backend…</p>}
        </section>
      )}
    </footer>
  )
}

export default function App() {
  return (
    <>
      <Navbar />
      <main className="wl-main app-shell">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/register" element={<Register />} />
          <Route path="/login" element={<Login />} />
          <Route path="/users/:userId" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route path="/users/:userId/followers" element={<ProtectedRoute><FollowList kind="followers" /></ProtectedRoute>} />
          <Route path="/users/:userId/following" element={<ProtectedRoute><FollowList kind="following" /></ProtectedRoute>} />
          <Route path="/settings/profile" element={<ProtectedRoute><EditProfile /></ProtectedRoute>} />
          <Route path="/moderation" element={<ProtectedRoute><ModerationPage /></ProtectedRoute>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <SystemStatus />
    </>
  )
}
