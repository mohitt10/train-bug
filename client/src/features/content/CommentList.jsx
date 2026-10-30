import { useState, useEffect } from 'react';
import { useCurrentUser } from '../../api/authBridge';
import { getComments, createComment } from '../../api/contentApi';
import { CommentItem } from './CommentItem';
import { Loading } from './Loading';
import { Empty } from './Empty';
import { ErrorMessage } from './ErrorMessage';

export function CommentList({ postId, onCommentCountChange }) {
  const { isLoggedIn } = useCurrentUser();
  const [comments, setComments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Comment composer state
  const [commentText, setCommentText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [composerError, setComposerError] = useState('');

  const loadComments = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await getComments(postId);
      setComments(data.items || []);
    } catch (err) {
      setError(err.message || 'Could not load comments.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadComments();
  }, [postId]);

  const handleCreateComment = async (e) => {
    e.preventDefault();
    const trimmed = commentText.trim();
    if (!trimmed) {
      setComposerError('Comment content cannot be empty.');
      return;
    }
    if (trimmed.length > 2000) {
      setComposerError('Comment exceeds 2,000 character limit.');
      return;
    }

    setIsSubmitting(true);
    setComposerError('');
    try {
      const newComment = await createComment(postId, { content: trimmed });
      setComments((prev) => [...prev, newComment]);
      setCommentText('');
      if (onCommentCountChange) {
        onCommentCountChange(1);
      }
    } catch (err) {
      setComposerError(err.message || 'Could not post comment.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCommentUpdated = (updated) => {
    setComments((prev) =>
      prev.map((c) => (c.comment_id === updated.comment_id ? updated : c))
    );
  };

  const handleCommentDeleted = (commentId) => {
    setComments((prev) => prev.filter((c) => c.comment_id !== commentId));
    if (onCommentCountChange) {
      onCommentCountChange(-1);
    }
  };

  return (
    <section className="comments-section" aria-label="Comments">
      <h3 className="section-title">Discussion ({comments.length})</h3>

      {isLoggedIn ? (
        <form className="comment-composer" onSubmit={handleCreateComment}>
          <textarea
            className="form-textarea"
            rows={3}
            value={commentText}
            placeholder="Write a comment on this post…"
            disabled={isSubmitting}
            onChange={(e) => {
              setCommentText(e.target.value);
              if (composerError) setComposerError('');
            }}
          />
          <div className="comment-composer-footer">
            <span
              className={`counter ${
                commentText.length > 2000 ? 'counter-danger' : 'counter-muted'
              }`}
            >
              {commentText.length} / 2000
            </span>
            {composerError && (
              <span className="counter-error-inline">{composerError}</span>
            )}
            <button
              type="submit"
              className="btn btn-primary btn-sm"
              disabled={
                isSubmitting ||
                !commentText.trim() ||
                commentText.length > 2000
              }
            >
              {isSubmitting ? 'Posting…' : 'Post Comment'}
            </button>
          </div>
        </form>
      ) : (
        <div className="login-notice">
          <p>Select a dev user from the top bar to join the discussion.</p>
        </div>
      )}

      {isLoading ? (
        <Loading message="Loading discussion…" />
      ) : error ? (
        <ErrorMessage message={error} onRetry={loadComments} />
      ) : comments.length === 0 ? (
        <Empty
          title="No comments yet"
          description="Start the conversation by sharing your thoughts above."
        />
      ) : (
        <div className="comments-list">
          {comments.map((comment) => (
            <CommentItem
              key={comment.comment_id}
              comment={comment}
              onCommentUpdated={handleCommentUpdated}
              onCommentDeleted={handleCommentDeleted}
            />
          ))}
        </div>
      )}
    </section>
  );
}
