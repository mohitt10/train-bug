import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.js'

export default function Navbar() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <header className="wl-nav">
      <Link to="/" className="wl-brand">WanderLog</Link>
      <nav>
        {loading ? null : user ? (
          <>
            <Link to={`/users/${user.user_id}`}>@{user.username}</Link>
            <Link to="/moderation">Moderation</Link>
            <button type="button" className="wl-btn wl-btn-quiet" onClick={handleLogout}>
              Log out
            </button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/register">Sign up</Link>
          </>
        )}
      </nav>
    </header>
  )
}
