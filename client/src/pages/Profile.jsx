import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getUser } from '../api/userApi.js'
import FollowButton from '../components/FollowButton.jsx'
import { useAuth } from '../context/AuthContext.js'

function ProfileView({ userId }) {
  const { user: me } = useAuth()
  const [profile, setProfile] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    getUser(userId)
      .then((data) => {
        if (!cancelled) setProfile(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [userId])

  if (error) return <p className="wl-error" role="alert">{error}</p>
  if (!profile) return <p className="wl-muted">Loading…</p>

  const isOwnProfile = me.user_id === profile.user_id
  const joined = new Date(profile.created_at).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
  })

  function handleFollowChange(result) {
    setProfile({
      ...profile,
      is_following: result.following,
      follower_count: result.follower_count,
      following_count: result.following_count,
    })
  }

  return (
    <section>
      <h1>{profile.display_name || profile.username}</h1>
      <p className="wl-muted">@{profile.username} · Joined {joined}</p>
      {profile.bio && <p>{profile.bio}</p>}

      <p className="wl-counts">
        <Link to={`/users/${profile.user_id}/followers`}>
          <strong>{profile.follower_count}</strong> {profile.follower_count === 1 ? 'follower' : 'followers'}
        </Link>
        <Link to={`/users/${profile.user_id}/following`}>
          <strong>{profile.following_count}</strong> following
        </Link>
      </p>

      {isOwnProfile ? (
        <Link to="/settings/profile" className="wl-btn">Edit profile</Link>
      ) : (
        <FollowButton
          userId={profile.user_id}
          isFollowing={profile.is_following}
          onChange={handleFollowChange}
        />
      )}
    </section>
  )
}

export default function Profile() {
  const { userId } = useParams()
  // key resets the component's state when navigating between profiles
  return <ProfileView key={userId} userId={userId} />
}
