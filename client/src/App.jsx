import { Navigate, Route, Routes } from 'react-router-dom'
import './phase2.css'
import Navbar from './components/Navbar.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import { useAuth } from './context/AuthContext.js'
import EditProfile from './pages/EditProfile.jsx'
import FollowList from './pages/FollowList.jsx'
import Login from './pages/Login.jsx'
import Profile from './pages/Profile.jsx'
import Register from './pages/Register.jsx'

// Phase 3 will replace this with the feed at "/".
function Home() {
  const { user, loading } = useAuth()
  if (loading) return <p className="wl-muted">Loading…</p>
  return <Navigate to={user ? `/users/${user.user_id}` : '/login'} replace />
}

function NotFound() {
  return <p>Page not found.</p>
}

export default function App() {
  return (
    <>
      <Navbar />
      <main className="wl-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/register" element={<Register />} />
          <Route path="/login" element={<Login />} />
          <Route path="/users/:userId" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route path="/users/:userId/followers" element={<ProtectedRoute><FollowList kind="followers" /></ProtectedRoute>} />
          <Route path="/users/:userId/following" element={<ProtectedRoute><FollowList kind="following" /></ProtectedRoute>} />
          <Route path="/settings/profile" element={<ProtectedRoute><EditProfile /></ProtectedRoute>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </>
  )
}
