export function ConfirmDelete({
  title = 'Delete this item?',
  message = 'This action cannot be undone and will remove all nested replies.',
  isOpen,
  onConfirm,
  onCancel,
  isDeleting = false,
}) {
  if (!isOpen) return null;

  return (
    <div className="confirm-overlay" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
      <div className="confirm-card">
        <h3 id="confirm-title">{title}</h3>
        <p className="confirm-message">{message}</p>
        <div className="confirm-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onCancel}
            disabled={isDeleting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-danger btn-sm"
            onClick={onConfirm}
            disabled={isDeleting}
          >
            {isDeleting ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}
