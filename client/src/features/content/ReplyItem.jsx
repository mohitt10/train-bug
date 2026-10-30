import { useState } from 'react';
import { useCurrentUser } from '../../api/authBridge';
import { updateReply, deleteReply } from '../../api/contentApi';
import { formatRelativeTime, isEdited } from './timeUtils';
import { EditableText } from './EditableText';
import { ConfirmDelete } from './ConfirmDelete';

export function ReplyItem({ reply, onReplyUpdated, onReplyDeleted }) {
  const { user } = useCurrentUser();
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionError, setActionError] = useState('');

  const isOwner = Boolean(user && user.user_id === reply.user_id);
  const edited = isEdited(reply.created_at, reply.updated_at);

  const handleSaveEdit = async (newContent) => {
    setIsSaving(true);
    setActionError('');
    try {
      const updated = await updateReply(reply.reply_id, { content: newContent });
      setIsEditing(false);
      onReplyUpdated(updated);
    } catch (err) {
      setActionError(err.message || 'Could not update reply.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    setActionError('');
    try {
      await deleteReply(reply.reply_id);
      setShowConfirm(false);
      onReplyDeleted(reply.reply_id);
    } catch (err) {
      setActionError(err.message || 'Could not delete reply.');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <article className="reply-card">
      <header className="content-header">
        <div className="author-meta">
          <strong className="author-name">
            {reply.display_name || reply.author?.display_name || 'Traveler'}
          </strong>
          <span className="author-handle">
            @{reply.username || reply.author?.username || 'user'}
          </span>
          <span className="meta-separator">•</span>
          <time dateTime={reply.created_at} className="content-time">
            {formatRelativeTime(reply.created_at)}
          </time>
          {edited && <span className="edited-badge">(edited)</span>}
        </div>

        {isOwner && !isEditing && (
          <div className="card-actions">
            <button
              type="button"
              className="action-link"
              onClick={() => setIsEditing(true)}
              title="Edit reply"
            >
              Edit
            </button>
            <span className="meta-separator">•</span>
            <button
              type="button"
              className="action-link action-link-danger"
              onClick={() => setShowConfirm(true)}
              title="Delete reply"
            >
              Delete
            </button>
          </div>
        )}
      </header>

      {actionError && <div className="card-error-inline">{actionError}</div>}

      {isEditing ? (
        <EditableText
          initialValue={reply.content}
          maxLength={2000}
          placeholder="Edit your reply…"
          isSaving={isSaving}
          onSave={handleSaveEdit}
          onCancel={() => {
            setIsEditing(false);
            setActionError('');
          }}
          minRows={2}
        />
      ) : (
        <p className="content-body text-reply">{reply.content}</p>
      )}

      <ConfirmDelete
        isOpen={showConfirm}
        title="Delete reply?"
        message="Are you sure you want to delete this reply?"
        isDeleting={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setShowConfirm(false)}
      />
    </article>
  );
}
