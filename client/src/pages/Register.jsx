import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.js'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', display_name: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  async function handleSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const user = await register(form)
      navigate(`/users/${user.user_id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="wl-narrow">
      <h1>Create your account</h1>
      <form onSubmit={handleSubmit} className="wl-form">
        <label>
          Username
          <input value={form.username} onChange={update('username')} autoComplete="username"
                 required minLength={3} maxLength={50} />
        </label>
        <label>
          Email
          <input type="email" value={form.email} onChange={update('email')}
                 autoComplete="email" required maxLength={255} />
        </label>
        <label>
          Display name (optional)
          <input value={form.display_name} onChange={update('display_name')} maxLength={100} />
        </label>
        <label>
          Password
          <input type="password" value={form.password} onChange={update('password')}
                 autoComplete="new-password" required minLength={8} maxLength={128} />
        </label>
        {error && <p className="wl-error" role="alert">{error}</p>}
        <button type="submit" className="wl-btn wl-btn-primary" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="wl-muted">Already have an account? <Link to="/login">Log in</Link></p>
    </section>
  )
}
