import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useCurrentUser } from '../../api/authBridge';
import { getReplies, createReply } from '../../api/contentApi';
import { ReplyItem } from './ReplyItem';
import { Loading } from './Loading';
import { ErrorMessage } from './ErrorMessage';

export function ReplyList({ commentId, onReplyCountChange }) {
  const { isLoggedIn } = useCurrentUser();
  const [replies, setReplies] = useState([]);
  const [loadedCommentId, setLoadedCommentId] = useState(null);
  const isLoading = loadedCommentId !== commentId;
  const [error, setError] = useState('');

  // New reply composer state
  const [replyText, setReplyText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [composerError, setComposerError] = useState('');

  useEffect(() => {
    const controller = new AbortController();

    async function fetchReplies() {
      try {
        const data = await getReplies(commentId, { signal: controller.signal });
        setReplies(data.items || []);
        setError('');
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Could not load replies.');
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadedCommentId(commentId);
        }
      }
    }

    fetchReplies();

    return () => {
      controller.abort();
    };
  }, [commentId]);

  const handleRetry = () => {
    setLoadedCommentId(null);
    setError('');
    getReplies(commentId)
      .then((data) => setReplies(data.items || []))
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Could not load replies.');
        }
      })
      .finally(() => setLoadedCommentId(commentId));
  };

  const handleCreateReply = async (e) => {
    e.preventDefault();
    const trimmed = replyText.trim();
    if (!trimmed) {
      setComposerError('Reply content cannot be empty.');
      return;
    }
    if (trimmed.length > 2000) {
      setComposerError('Reply exceeds 2,000 character limit.');
      return;
    }

    setIsSubmitting(true);
    setComposerError('');
    try {
      const newReply = await createReply(commentId, { content: trimmed });
      setReplies((prev) => [...prev, newReply]);
      setReplyText('');
      if (onReplyCountChange) {
        onReplyCountChange(1);
      }
    } catch (err) {
      setComposerError(err.message || 'Could not post reply.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReplyUpdated = (updated) => {
    setReplies((prev) =>
      prev.map((r) => (r.reply_id === updated.reply_id ? updated : r))
    );
  };

  const handleReplyDeleted = (replyId) => {
    setReplies((prev) => prev.filter((r) => r.reply_id !== replyId));
    if (onReplyCountChange) {
      onReplyCountChange(-1);
    }
  };

  return (
    <div className="replies-section">
      {isLoading ? (
        <Loading message="Loading replies…" />
      ) : error ? (
        <ErrorMessage message={error} onRetry={handleRetry} />
      ) : (
        <div className="replies-list">
          {replies.map((reply) => (
            <ReplyItem
              key={reply.reply_id}
              reply={reply}
              onReplyUpdated={handleReplyUpdated}
              onReplyDeleted={handleReplyDeleted}
            />
          ))}
        </div>
      )}

      {isLoggedIn ? (
        <form className="reply-composer" onSubmit={handleCreateReply}>
          <textarea
            className="form-textarea form-textarea-sm"
            rows={2}
            value={replyText}
            placeholder="Write a reply…"
            disabled={isSubmitting}
            onChange={(e) => {
              setReplyText(e.target.value);
              if (composerError) setComposerError('');
            }}
          />
          <div className="reply-composer-footer">
            <span
              className={`counter ${
                replyText.length > 2000 ? 'counter-danger' : 'counter-muted'
              }`}
            >
              {replyText.length} / 2000
            </span>
            {composerError && (
              <span className="counter-error-inline">{composerError}</span>
            )}
            <button
              type="submit"
              className="btn btn-primary btn-sm"
              disabled={
                isSubmitting ||
                !replyText.trim() ||
                replyText.length > 2000
              }
            >
              {isSubmitting ? 'Posting…' : 'Reply'}
            </button>
          </div>
        </form>
      ) : (
        <p className="login-prompt"><Link to="/login">Log in</Link> to reply.</p>
      )}
    </div>
  );
}
