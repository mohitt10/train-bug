import { useEffect, useState } from 'react';
import './App.css';
import './features/content/content.css';
import { FeedPage } from './features/content/FeedPage';

function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState('');
  const [showStatus, setShowStatus] = useState(false);

  useEffect(() => {
    async function checkApi() {
      try {
        const response = await fetch('/api/health');

        if (!response.ok) {
          throw new Error(`API returned HTTP ${response.status}`);
        }

        const data = await response.json();
        setHealth(data);
        setError('');
      } catch (requestError) {
        setHealth(null);
        setError(requestError.message);
      }
    }

    checkApi();
  }, []);

  return (
    <main className="app-shell">
      <header className="app-header">
        <p className="eyebrow">WanderLog • Phase 3</p>
        <h1>WanderLog</h1>
        <p className="description">
          A text-only social media platform for travelers and wanderers.
        </p>
      </header>

      {/* Primary Phase 3 Content Feature */}
      <FeedPage />

      {/* Preserved Backend Status (Collapsible Footer) */}
      <footer className="api-footer">
        <button
          type="button"
          className="btn-status-toggle"
          onClick={() => setShowStatus((prev) => !prev)}
        >
          {showStatus ? '▲ Hide System Status' : '▼ System Status'}
        </button>

        {showStatus && (
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
        )}
      </footer>
    </main>
  );
}

export default App;
