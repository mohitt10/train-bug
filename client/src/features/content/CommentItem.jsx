import { useState } from 'react';
import { useCurrentUser } from '../../api/authBridge';
import { updateComment, deleteComment } from '../../api/contentApi';
import { formatRelativeTime, isEdited } from './timeUtils';
import { EditableText } from './EditableText';
import { ConfirmDelete } from './ConfirmDelete';
import { ReplyList } from './ReplyList';

export function CommentItem({ comment, onCommentUpdated, onCommentDeleted }) {
  const { user } = useCurrentUser();
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionError, setActionError] = useState('');
  const [showReplies, setShowReplies] = useState(false);
  const [replyCount, setReplyCount] = useState(comment.reply_count || 0);

  const isOwner = Boolean(user && user.user_id === comment.user_id);
  const edited = isEdited(comment.created_at, comment.updated_at);

  const handleSaveEdit = async (newContent) => {
    setIsSaving(true);
    setActionError('');
    try {
      const updated = await updateComment(comment.comment_id, { content: newContent });
      setIsEditing(false);
      onCommentUpdated(updated);
    } catch (err) {
      setActionError(err.message || 'Could not update comment.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    setActionError('');
    try {
      await deleteComment(comment.comment_id);
      setShowConfirm(false);
      onCommentDeleted(comment.comment_id);
    } catch (err) {
      setActionError(err.message || 'Could not delete comment.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleReplyCountChange = (delta) => {
    setReplyCount((prev) => Math.max(0, prev + delta));
  };

  return (
    <article className="comment-card">
      <header className="content-header">
        <div className="author-meta">
          <strong className="author-name">
            {comment.display_name || comment.author?.display_name || 'Traveler'}
          </strong>
          <span className="author-handle">
            @{comment.username || comment.author?.username || 'user'}
          </span>
          <span className="meta-separator">•</span>
          <time dateTime={comment.created_at} className="content-time">
            {formatRelativeTime(comment.created_at)}
          </time>
          {edited && <span className="edited-badge">(edited)</span>}
        </div>

        {isOwner && !isEditing && (
          <div className="card-actions">
            <button
              type="button"
              className="action-link"
              onClick={() => setIsEditing(true)}
              title="Edit comment"
            >
              Edit
            </button>
            <span className="meta-separator">•</span>
            <button
              type="button"
              className="action-link action-link-danger"
              onClick={() => setShowConfirm(true)}
              title="Delete comment"
            >
              Delete
            </button>
          </div>
        )}
      </header>

      {actionError && <div className="card-error-inline">{actionError}</div>}

      {isEditing ? (
        <EditableText
          initialValue={comment.content}
          maxLength={2000}
          placeholder="Edit your comment…"
          isSaving={isSaving}
          onSave={handleSaveEdit}
          onCancel={() => {
            setIsEditing(false);
            setActionError('');
          }}
          minRows={3}
        />
      ) : (
        <p className="content-body text-comment">{comment.content}</p>
      )}

      <footer className="comment-footer">
        <button
          type="button"
          className="btn-toggle-replies"
          onClick={() => setShowReplies((prev) => !prev)}
        >
          {showReplies ? 'Hide replies' : `💬 Replies (${replyCount})`}
        </button>
      </footer>

      {showReplies && (
        <ReplyList
          commentId={comment.comment_id}
          onReplyCountChange={handleReplyCountChange}
        />
      )}

      <ConfirmDelete
        isOpen={showConfirm}
        title="Delete comment?"
        message="Are you sure you want to delete this comment? Its replies will also be removed."
        isDeleting={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setShowConfirm(false)}
      />
    </article>
  );
}
