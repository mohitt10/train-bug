import { useState } from 'react'
import { followUser, unfollowUser } from '../api/userApi.js'

// onChange receives { following, follower_count, following_count } from the server.
export default function FollowButton({ userId, isFollowing, onChange }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function toggle() {
    setBusy(true)
    setError('')
    try {
      const result = isFollowing ? await unfollowUser(userId) : await followUser(userId)
      onChange(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <span>
      <button
        type="button"
        className={isFollowing ? 'wl-btn' : 'wl-btn wl-btn-primary'}
        onClick={toggle}
        disabled={busy}
      >
        {isFollowing ? 'Unfollow' : 'Follow'}
      </button>
      {error && <span className="wl-error" role="alert"> {error}</span>}
    </span>
  )
}
