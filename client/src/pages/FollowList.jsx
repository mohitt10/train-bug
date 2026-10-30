import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getFollowers, getFollowing } from '../api/userApi.js'
import UserList from '../components/UserList.jsx'

function FollowListView({ userId, kind }) {
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const fetchPage = kind === 'followers' ? getFollowers : getFollowing
    fetchPage(userId, page)
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [userId, kind, page])

  const title = kind === 'followers' ? 'Followers' : 'Following'
  const loading = !error && (!data || data.page !== page)
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.limit)) : 1

  return (
    <section>
      <p><Link to={`/users/${userId}`}>← Back to profile</Link></p>
      <h1>{title}</h1>
      {error && <p className="wl-error" role="alert">{error}</p>}
      {loading && <p className="wl-muted">Loading…</p>}
      {!loading && data && (
        <>
          <UserList
            items={data.items}
            emptyText={kind === 'followers' ? 'No followers yet.' : 'Not following anyone yet.'}
          />
          {lastPage > 1 && (
            <div className="wl-row">
              <button type="button" className="wl-btn" disabled={page <= 1}
                      onClick={() => setPage(page - 1)}>Previous</button>
              <span className="wl-muted">Page {page} of {lastPage}</span>
              <button type="button" className="wl-btn" disabled={page >= lastPage}
                      onClick={() => setPage(page + 1)}>Next</button>
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default function FollowList({ kind }) {
  const { userId } = useParams()
  return <FollowListView key={`${userId}-${kind}`} userId={userId} kind={kind} />
}
