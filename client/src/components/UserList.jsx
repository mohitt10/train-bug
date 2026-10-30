import { Link } from 'react-router-dom'

export default function UserList({ items, emptyText }) {
  if (items.length === 0) return <p className="wl-muted">{emptyText}</p>
  return (
    <ul className="wl-list">
      {items.map((u) => (
        <li key={u.user_id}>
          <Link to={`/users/${u.user_id}`}>
            <strong>{u.display_name || u.username}</strong>
            <span className="wl-muted"> @{u.username}</span>
          </Link>
        </li>
      ))}
    </ul>
  )
}
