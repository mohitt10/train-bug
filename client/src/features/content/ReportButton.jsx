import { useState } from 'react';
import { useCurrentUser } from '../../api/authBridge';
import { reportResource } from '../../api/contentApi';

export function ReportButton({ targetType, targetId }) {
  const { isLoggedIn } = useCurrentUser();
  const [isOpen, setIsOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  if (!isLoggedIn) return null;

  const submitReport = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError('');
    try {
      await reportResource(targetType, targetId, reason);
      setNotice('Report submitted for moderator review.');
      setReason('');
      setIsOpen(false);
    } catch (requestError) {
      setError(requestError.message || 'Could not submit report.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <span className="report-action">
      <button type="button" className="action-link" onClick={() => setIsOpen((open) => !open)}>
        Report
      </button>
      {notice && <span className="social-action-notice" role="status">{notice}</span>}
      {error && <span className="social-action-error" role="alert">{error}</span>}
      {isOpen && (
        <form className="report-form" onSubmit={submitReport}>
          <label>
            Why are you reporting this {targetType}?
            <textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              maxLength={500}
              rows={3}
              required
              disabled={isSubmitting}
            />
          </label>
          <div className="report-form-actions">
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setIsOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary btn-sm" disabled={isSubmitting || !reason.trim()}>
              {isSubmitting ? 'Submitting…' : 'Submit report'}
            </button>
          </div>
        </form>
      )}
    </span>
  );
}
