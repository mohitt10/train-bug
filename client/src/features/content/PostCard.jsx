import { useState } from 'react';
import { useCurrentUser } from '../../api/authBridge';
import { updatePost, deletePost } from '../../api/contentApi';
import { formatRelativeTime, isEdited } from './timeUtils';
import { ConfirmDelete } from './ConfirmDelete';
import { CommentList } from './CommentList';

export function PostCard({
  post,
  onPostUpdated,
  onPostDeleted,
  onAuthorClick,
  onOpenDetail,
  onCommentCountChange,
  isDetailView = false,
}) {
  const { user } = useCurrentUser();
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(post.title || '');
  const [editContent, setEditContent] = useState(post.content || '');
  const [editLocation, setEditLocation] = useState(post.location || '');
  const [isSaving, setIsSaving] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionError, setActionError] = useState('');
  const [showComments, setShowComments] = useState(isDetailView);

  const isOwner = Boolean(user && user.user_id === post.user_id);
  const edited = isEdited(post.created_at, post.updated_at);

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    const trimmedContent = editContent.trim();
    if (!trimmedContent) {
      setActionError('Post content cannot be empty.');
      return;
    }

    setIsSaving(true);
    setActionError('');
    try {
      const updated = await updatePost(post.post_id, {
        title: editTitle.trim() || null,
        content: trimmedContent,
        location: editLocation.trim() || null,
      });
      setIsEditing(false);
      if (onPostUpdated) {
        onPostUpdated(updated);
      }
    } catch (err) {
      setActionError(err.message || 'Could not update post.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    setActionError('');
    try {
      await deletePost(post.post_id);
      setShowConfirm(false);
      if (onPostDeleted) {
        onPostDeleted(post.post_id);
      }
    } catch (err) {
      setActionError(err.message || 'Could not delete post.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCommentCountDelta = (delta) => {
    if (onCommentCountChange) {
      onCommentCountChange(post.post_id, delta);
    }
  };

  return (
    <article className="card post-card">
      <header className="content-header">
        <div className="author-meta">
          <button
            type="button"
            className="author-button"
            onClick={() => onAuthorClick && onAuthorClick(post.user_id)}
          >
            <strong className="author-name">
              {post.display_name || post.author?.display_name || 'Traveler'}
            </strong>
            <span className="author-handle">
              @{post.username || post.author?.username || 'user'}
            </span>
          </button>
          <span className="meta-separator">•</span>
          <time dateTime={post.created_at} className="content-time">
            {formatRelativeTime(post.created_at)}
          </time>
          {edited && <span className="edited-badge">(edited)</span>}
        </div>

        {isOwner && !isEditing && (
          <div className="card-actions">
            <button
              type="button"
              className="action-link"
              onClick={() => {
                setEditTitle(post.title || '');
                setEditContent(post.content || '');
                setEditLocation(post.location || '');
                setIsEditing(true);
              }}
              title="Edit post"
            >
              Edit
            </button>
            <span className="meta-separator">•</span>
            <button
              type="button"
              className="action-link action-link-danger"
              onClick={() => setShowConfirm(true)}
              title="Delete post"
            >
              Delete
            </button>
          </div>
        )}
      </header>

      {post.location && !isEditing && (
        <div className="post-location">
          <span>📍 {post.location}</span>
        </div>
      )}

      {actionError && <div className="card-error-inline">{actionError}</div>}

      {isEditing ? (
        <form onSubmit={handleSaveEdit} className="post-edit-form">
          <div className="form-group">
            <input
              type="text"
              className="form-input"
              placeholder="Title (optional, max 200)"
              maxLength={200}
              value={editTitle}
              disabled={isSaving}
              onChange={(e) => setEditTitle(e.target.value)}
            />
          </div>

          <div className="form-group">
            <textarea
              className="form-textarea"
              rows={4}
              placeholder="Content…"
              value={editContent}
              disabled={isSaving}
              onChange={(e) => setEditContent(e.target.value)}
            />
          </div>

          <div className="form-group">
            <input
              type="text"
              className="form-input form-input-sm"
              placeholder="Location (optional, max 100)"
              maxLength={100}
              value={editLocation}
              disabled={isSaving}
              onChange={(e) => setEditLocation(e.target.value)}
            />
          </div>

          <div className="editable-text-footer">
            <span className="counter counter-muted">{editContent.length} chars</span>
            <div className="editable-text-actions">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setIsEditing(false);
                  setActionError('');
                }}
                disabled={isSaving}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary btn-sm"
                disabled={isSaving || !editContent.trim()}
              >
                {isSaving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </form>
      ) : (
        <div className="post-body">
          {post.title && <h3 className="post-title">{post.title}</h3>}
          <p className="content-body text-post">{post.content}</p>
        </div>
      )}

      <footer className="post-footer">
        <button
          type="button"
          className="btn-toggle-comments"
          onClick={() => {
            if (isDetailView) return;
            setShowComments((prev) => !prev);
          }}
        >
          💬 Comments ({post.comment_count || 0})
        </button>

        {!isDetailView && onOpenDetail && (
          <button
            type="button"
            className="action-link action-link-view"
            onClick={() => onOpenDetail(post.post_id)}
          >
            Open Thread ↗
          </button>
        )}
      </footer>

      {showComments && (
        <CommentList
          postId={post.post_id}
          onCommentCountChange={handleCommentCountDelta}
        />
      )}

      <ConfirmDelete
        isOpen={showConfirm}
        title="Delete post?"
        message="Are you sure you want to delete this post? All nested comments and replies will be permanently deleted."
        isDeleting={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setShowConfirm(false)}
      />
    </article>
  );
}
