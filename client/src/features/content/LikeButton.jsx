import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCurrentUser } from '../../api/authBridge';
import { likeResource, unlikeResource } from '../../api/contentApi';

export function LikeButton({ targetType, targetId, count = 0, liked = false }) {
  const { isLoggedIn } = useCurrentUser();
  const [likeCount, setLikeCount] = useState(count);
  const [isLiked, setIsLiked] = useState(liked);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');

  const toggleLike = async () => {
    if (isSaving) return;
    setIsSaving(true);
    setError('');
    try {
      const result = isLiked
        ? await unlikeResource(targetType, targetId)
        : await likeResource(targetType, targetId);
      setLikeCount(result.like_count);
      setIsLiked(result.liked_by_me);
    } catch (requestError) {
      setError(requestError.message || 'Could not update like.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <span className="social-action">
      {!isLoggedIn && <Link className="action-link" to="/login">♡ Like ({likeCount})</Link>}
      {isLoggedIn && (
      <button type="button" className="action-link" onClick={toggleLike} disabled={isSaving}>
        {isSaving ? 'Saving…' : `${isLiked ? '♥ Liked' : '♡ Like'} (${likeCount})`}
      </button>
      )}
      {error && <span className="social-action-error" role="alert">{error}</span>}
    </span>
  );
}
