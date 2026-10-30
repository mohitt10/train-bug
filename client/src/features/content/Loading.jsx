export function Loading({ message = 'Loading content…' }) {
  return (
    <div className="status-box status-loading" role="status">
      <span className="spinner" aria-hidden="true" />
      <p>{message}</p>
    </div>
  );
}
