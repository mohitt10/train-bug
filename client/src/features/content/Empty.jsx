export function Empty({
  title = 'No content yet',
  description = 'Be the first traveler to share a note.',
  action,
}) {
  return (
    <div className="status-box status-empty">
      <h3>{title}</h3>
      <p>{description}</p>
      {action && <div className="status-action">{action}</div>}
    </div>
  );
}
