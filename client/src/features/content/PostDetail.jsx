import { useState, useEffect } from 'react';
import { getPost } from '../../api/contentApi';
import { PostCard } from './PostCard';
import { Loading } from './Loading';
import { ErrorMessage } from './ErrorMessage';

export function PostDetail({ postId, onBack }) {
  const [post, setPost] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const loadPost = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await getPost(postId);
      setPost(data);
    } catch (err) {
      setError(err.message || 'Could not load post details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPost();
  }, [postId]);

  const handlePostUpdated = (updated) => {
    setPost(updated);
  };

  const handlePostDeleted = () => {
    if (onBack) {
      onBack();
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
        <ErrorMessage message={error} onRetry={loadPost} />
      ) : post ? (
        <PostCard
          post={post}
          isDetailView={true}
          onPostUpdated={handlePostUpdated}
          onPostDeleted={handlePostDeleted}
        />
      ) : null}
    </div>
  );
}
