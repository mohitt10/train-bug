import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    async function checkApi() {
      try {
        const response = await fetch('/api/health')

        if (!response.ok) {
          throw new Error(`API returned HTTP ${response.status}`)
        }

        const data = await response.json()
        setHealth(data)
        setError('')
      } catch (requestError) {
        setHealth(null)
        setError(requestError.message)
      }
    }

    checkApi()
  }, [])

  return (
    <main className="app-shell">
      <p className="eyebrow">Social media platform</p>
      <h1>React + Flask</h1>
      <p className="description">
        React renders the interface; Flask provides the API.
      </p>

      <section className="api-card" aria-live="polite">
        <h2>Backend status</h2>

        {health && (
          <p className="status status-connected">
            Connected — {health.service}
          </p>
        )}

        {error && (
          <p className="status status-error">
            Could not connect to the backend: {error}
          </p>
        )}

        {!health && !error && <p className="status">Checking backend…</p>}
      </section>
    </main>
  )
}

export default App