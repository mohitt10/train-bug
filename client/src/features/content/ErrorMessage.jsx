export function ErrorMessage({ message, onRetry }) {
  if (!message) return null;

  return (
    <div className="status-box status-error-box" role="alert">
      <p className="error-text">⚠️ {message}</p>
      {onRetry && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
