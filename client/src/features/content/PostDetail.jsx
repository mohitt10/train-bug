import { useState, useEffect } from 'react';
import { getPost } from '../../api/contentApi';
import { PostCard } from './PostCard';
import { Loading } from './Loading';
import { ErrorMessage } from './ErrorMessage';

export function PostDetail({ postId, onBack, onPostUpdated, onPostDeleted, onCommentCountChange }) {
  const [post, setPost] = useState(null);
  const [loadedPostId, setLoadedPostId] = useState(null);
  const isLoading = loadedPostId !== postId;
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();

    async function fetchPost() {
      try {
        const data = await getPost(postId, { signal: controller.signal });
        setPost(data);
        setError('');
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Could not load post details.');
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadedPostId(postId);
        }
      }
    }

    fetchPost();

    return () => {
      controller.abort();
    };
  }, [postId]);

  const handleRetry = () => {
    setLoadedPostId(null);
    setError('');
    getPost(postId)
      .then((data) => setPost(data))
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Could not load post details.');
        }
      })
      .finally(() => setLoadedPostId(postId));
  };

  const handleUpdated = (updated) => {
    setPost(updated);
    if (onPostUpdated) {
      onPostUpdated(updated);
    }
  };

  const handleDeleted = (deletedId) => {
    if (onPostDeleted) {
      onPostDeleted(deletedId);
    }
    if (onBack) {
      onBack();
    }
  };

  const handleCommentCountDelta = (pId, delta) => {
    setPost((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        comment_count: Math.max(0, (prev.comment_count || 0) + delta),
      };
    });
    if (onCommentCountChange) {
      onCommentCountChange(pId, delta);
    }
  };

  return (
    <div className="post-detail-view">
      <div className="detail-navigation">
        <button type="button" className="btn btn-secondary btn-sm" onClick={onBack}>
          ← Back to feed
        </button>
      </div>

      {isLoading ? (
        <Loading message="Loading travel note…" />
      ) : error ? (
        <ErrorMessage message={error} onRetry={handleRetry} />
      ) : post ? (
        <PostCard
          post={post}
          isDetailView={true}
          onPostUpdated={handleUpdated}
          onPostDeleted={handleDeleted}
          onCommentCountChange={handleCommentCountDelta}
        />
      ) : null}
    </div>
  );
}
