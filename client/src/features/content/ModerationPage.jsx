import { useEffect, useState } from 'react';
import {
  getModerationReports,
  getModerator,
  getQueryHistory,
  reviewReport,
} from '../../api/contentApi';
import { ErrorMessage } from './ErrorMessage';
import { Loading } from './Loading';

const REPORT_FILTERS = ['pending', 'resolved', 'dismissed'];

export function ModerationPage() {
  const [moderator, setModerator] = useState(null);
  const [reports, setReports] = useState([]);
  const [status, setStatus] = useState('pending');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [reviewingId, setReviewingId] = useState(null);
  const [showInspector, setShowInspector] = useState(false);

  useEffect(() => {
    let active = true;
    getModerator()
      .then(async (identity) => {
        const result = await getModerationReports(status);
        if (active) {
          setModerator(identity);
          setReports(result.items);
          setError('');
        }
      })
      .catch((requestError) => {
        if (active) setError(requestError.message || 'Could not load moderation tools.');
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [status]);

  const changeStatus = async (reportId, newStatus) => {
    setReviewingId(reportId);
    setError('');
    try {
      const updated = await reviewReport(reportId, newStatus);
      setReports((items) => items.map((item) => item.report_id === reportId ? updated : item));
    } catch (requestError) {
      setError(requestError.message || 'Could not update report.');
    } finally {
      setReviewingId(null);
    }
  };

  if (isLoading) return <Loading message="Loading moderation dashboard…" />;
  if (!moderator) {
    return (
      <section className="moderation-page">
        <h1>Moderation</h1>
        <ErrorMessage message={error || 'Moderator access is required.'} />
      </section>
    );
  }

  return (
    <section className="moderation-page">
      <header className="moderation-heading">
        <div>
          <p className="eyebrow">Moderator dashboard</p>
          <h1>Community reports</h1>
          <p className="wl-muted">Signed in as @{moderator.username}</p>
        </div>
      </header>

      <div className="moderation-tabs" role="tablist" aria-label="Report status">
        {REPORT_FILTERS.map((filter) => (
          <button
            type="button"
            role="tab"
            aria-selected={status === filter}
            className={status === filter ? 'moderation-tab active' : 'moderation-tab'}
            key={filter}
            onClick={() => {
              setIsLoading(true);
              setStatus(filter);
            }}
          >
            {filter[0].toUpperCase() + filter.slice(1)}
          </button>
        ))}
      </div>

      {error && <ErrorMessage message={error} />}
      {reports.length === 0 ? (
        <div className="moderation-empty">
          <h2>No {status} reports</h2>
          <p>Reports will appear here when travelers flag content.</p>
        </div>
      ) : (
        <div className="report-list">
          {reports.map((report) => (
            <article className="report-card" key={report.report_id}>
              <header className="report-card-heading">
                <strong>Report #{report.report_id}</strong>
                <span className={`report-status status-${report.status}`}>{report.status}</span>
                <time dateTime={report.created_at}>{new Date(report.created_at).toLocaleString()}</time>
              </header>
              <dl className="report-details">
                <div><dt>Reported by</dt><dd>@{report.reporter.username}</dd></div>
                <div><dt>Target</dt><dd>{report.target.type} #{report.target.id}</dd></div>
                <div><dt>Reason</dt><dd>{report.reason}</dd></div>
                {report.target.content && (
                  <div><dt>Content</dt><dd className="report-content-preview">{report.target.content}</dd></div>
                )}
                {report.reviewer_username && (
                  <div><dt>Reviewed by</dt><dd>@{report.reviewer_username}</dd></div>
                )}
              </dl>
              {report.status === 'pending' && (
                <div className="report-review-actions">
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={reviewingId === report.report_id}
                    onClick={() => changeStatus(report.report_id, 'resolved')}
                  >
                    {reviewingId === report.report_id ? 'Saving…' : 'Resolve'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={reviewingId === report.report_id}
                    onClick={() => changeStatus(report.report_id, 'dismissed')}
                  >
                    Dismiss
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}

      <QueryInspector open={showInspector} onToggle={() => setShowInspector((open) => !open)} />
    </section>
  );
}

function QueryInspector({ open, onToggle }) {
  const [filters, setFilters] = useState({ operation: '', request_id: '', endpoint: '' });
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);

  const loadQueries = async (event) => {
    event?.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      const result = await getQueryHistory(filters);
      setEntries(result.items);
      setHasLoaded(true);
    } catch (requestError) {
      setError(requestError.message || 'Could not load query history.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="query-inspector">
      <button type="button" className="inspector-toggle" aria-expanded={open} onClick={onToggle}>
        <span>SQL Query Inspector</span>
        <span>{open ? 'Hide' : 'Show'}</span>
      </button>
      {open && (
        <div className="inspector-panel">
          <p className="wl-muted">
            Actual parameterized SQL templates and safe execution metadata captured by the backend.
            Parameter values are never included.
          </p>
          <form className="inspector-filters" onSubmit={loadQueries}>
            <label>
              Operation
              <select
                value={filters.operation}
                onChange={(event) => setFilters({ ...filters, operation: event.target.value })}
              >
                <option value="">All operations</option>
                {['SELECT', 'INSERT', 'UPDATE', 'DELETE'].map((operation) => (
                  <option key={operation} value={operation}>{operation}</option>
                ))}
              </select>
            </label>
            <label>
              Request ID
              <input
                value={filters.request_id}
                onChange={(event) => setFilters({ ...filters, request_id: event.target.value })}
                placeholder="Filter by request"
              />
            </label>
            <label>
              Endpoint/action
              <input
                value={filters.endpoint}
                onChange={(event) => setFilters({ ...filters, endpoint: event.target.value })}
                placeholder="Filter endpoint"
              />
            </label>
            <button type="submit" className="btn btn-primary btn-sm" disabled={isLoading}>
              {isLoading ? 'Loading…' : 'Apply filters'}
            </button>
          </form>
          {error && <ErrorMessage message={error} />}
          {isLoading && <Loading message="Loading captured queries…" />}
          {!isLoading && hasLoaded && entries.length === 0 && (
            <p className="moderation-empty">No captured queries match these filters.</p>
          )}
          {!isLoading && entries.length > 0 && (
            <div className="query-list">
              {entries.map((entry) => (
                <article className="query-entry" key={entry.query_id}>
                  <header>
                    <strong>{entry.operation}</strong>
                    <span className={`query-result status-${entry.status}`}>{entry.status}</span>
                    <time dateTime={entry.timestamp}>{new Date(entry.timestamp).toLocaleString()}</time>
                  </header>
                  <code className="query-action">{entry.endpoint} · {entry.action}</code>
                  <pre>{entry.statement}</pre>
                  <dl>
                    <div><dt>Duration</dt><dd>{entry.duration_ms} ms</dd></div>
                    <div><dt>Affected rows</dt><dd>{entry.affected_rows ?? '—'}</dd></div>
                    <div>
                      <dt>Request ID</dt>
                      <dd><button
                        type="button"
                        className="request-id-filter"
                        onClick={() => setFilters({ ...filters, request_id: entry.request_id || '' })}
                      >{entry.request_id || '—'}</button></dd>
                    </div>
                  </dl>
                  {entry.error_summary && <p className="query-error">{entry.error_summary}</p>}
                </article>
              ))}
            </div>
          )}
          {!hasLoaded && !isLoading && (
            <button type="button" className="btn btn-secondary btn-sm" onClick={loadQueries}>
              Load recent queries
            </button>
          )}
        </div>
      )}
    </section>
  );
}
