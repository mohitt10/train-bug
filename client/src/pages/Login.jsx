import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.js'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const user = await login(identifier, password)
      navigate(location.state?.from ?? `/users/${user.user_id}`, { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="wl-narrow">
      <h1>Log in</h1>
      <form onSubmit={handleSubmit} className="wl-form">
        <label>
          Username or email
          <input value={identifier} onChange={(e) => setIdentifier(e.target.value)}
                 autoComplete="username" required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                 autoComplete="current-password" required />
        </label>
        {error && <p className="wl-error" role="alert">{error}</p>}
        <button type="submit" className="wl-btn wl-btn-primary" disabled={busy}>
          {busy ? 'Logging in…' : 'Log in'}
        </button>
      </form>
      <p className="wl-muted">New here? <Link to="/register">Create an account</Link></p>
    </section>
  )
}
