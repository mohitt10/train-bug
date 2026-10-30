import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { updateMe } from '../api/userApi.js'
import { useAuth } from '../context/AuthContext.js'

export default function EditProfile() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()
  const [displayName, setDisplayName] = useState(user.display_name ?? '')
  const [bio, setBio] = useState(user.bio ?? '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const updated = await updateMe({ display_name: displayName, bio })
      setUser(updated)
      navigate(`/users/${updated.user_id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="wl-narrow">
      <h1>Edit profile</h1>
      <form onSubmit={handleSubmit} className="wl-form">
        <label>
          Display name
          <input value={displayName} onChange={(e) => setDisplayName(e.target.value)}
                 required maxLength={100} />
        </label>
        <label>
          Bio
          <textarea value={bio} onChange={(e) => setBio(e.target.value)} rows={4} maxLength={500} />
          <span className="wl-muted">{bio.length}/500</span>
        </label>
        {error && <p className="wl-error" role="alert">{error}</p>}
        <div className="wl-row">
          <button type="submit" className="wl-btn wl-btn-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save changes'}
          </button>
          <Link to={`/users/${user.user_id}`} className="wl-btn wl-btn-quiet">Cancel</Link>
        </div>
      </form>
    </section>
  )
}
