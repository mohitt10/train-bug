import { useState, useEffect } from 'react';
import { useCurrentUser } from '../../api/authBridge';
import { getFeed, getUserPosts } from '../../api/contentApi';
import { PostComposer } from './PostComposer';
import { PostCard } from './PostCard';
import { PostDetail } from './PostDetail';
import { Pagination } from './Pagination';
import { Loading } from './Loading';
import { Empty } from './Empty';
import { ErrorMessage } from './ErrorMessage';

export function FeedPage() {
  const { user, isLoggedIn, setDevUserId, availableDevUsers } = useCurrentUser();

  // Navigation state: either { view: 'feed' } or { view: 'detail', postId }
  const [navigation, setNavigation] = useState({ view: 'feed', postId: null });

  // Filtering by specific author (null for global feed)
  const [authorFilter, setAuthorFilter] = useState(null);

  const [posts, setPosts] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState('');

  const loadFeed = async (reset = true) => {
    if (reset) {
      setIsLoading(true);
      setError('');
    } else {
      setIsLoadingMore(true);
    }

    try {
      const cursor = reset ? null : nextCursor;
      let data;

      if (authorFilter) {
        data = await getUserPosts(authorFilter, cursor);
      } else {
        data = await getFeed(cursor);
      }

      if (reset) {
        setPosts(data.items || []);
      } else {
        setPosts((prev) => [...prev, ...(data.items || [])]);
      }
      setNextCursor(data.next_cursor || null);
    } catch (err) {
      setError(err.message || 'Could not fetch posts.');
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  };

  useEffect(() => {
    loadFeed(true);
  }, [authorFilter]);

  const handlePostCreated = (newPost) => {
    setPosts((prev) => [newPost, ...prev]);
  };

  const handlePostUpdated = (updated) => {
    setPosts((prev) =>
      prev.map((p) => (p.post_id === updated.post_id ? updated : p))
    );
  };

  const handlePostDeleted = (postId) => {
    setPosts((prev) => prev.filter((p) => p.post_id !== postId));
  };

  const handleAuthorClick = (authorId) => {
    setAuthorFilter(authorId);
    setNavigation({ view: 'feed', postId: null });
  };

  const handleOpenDetail = (postId) => {
    setNavigation({ view: 'detail', postId });
  };

  const handleBackToFeed = () => {
    setNavigation({ view: 'feed', postId: null });
  };

  return (
    <div className="content-container">
      {/* Dev User Switcher Bar */}
      <section className="dev-auth-bar" aria-label="Dev User Switcher">
        <div className="dev-auth-content">
          <span className="dev-tag">Phase 3 Dev Auth</span>
          <div className="dev-user-select-group">
            <label htmlFor="dev-user-select">Acting as:</label>
            <select
              id="dev-user-select"
              className="dev-user-select"
              value={user ? user.user_id : ''}
              onChange={(e) => setDevUserId(e.target.value)}
            >
              <option value="">Logged out (Guest)</option>
              {availableDevUsers.map((u) => (
                <option key={u.user_id} value={u.user_id}>
                  {u.display_name} (@{u.username})
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Main Content Area */}
      {navigation.view === 'detail' ? (
        <PostDetail
          postId={navigation.postId}
          onBack={handleBackToFeed}
        />
      ) : (
        <>
          {/* Feed Filter / Header */}
          <div className="feed-header-bar">
            {authorFilter ? (
              <div className="filter-pill">
                <span>Showing posts by traveler #{authorFilter}</span>
                <button
                  type="button"
                  className="filter-clear-btn"
                  onClick={() => setAuthorFilter(null)}
                >
                  ✕ View All Posts
                </button>
              </div>
            ) : (
              <div className="feed-title-wrapper">
                <h2>Travel Feed</h2>
                <p className="feed-subtitle">Stories, itineraries, and trail notes from travelers</p>
              </div>
            )}
          </div>

          {/* Composer (only on global feed or own timeline) */}
          <PostComposer onPostCreated={handlePostCreated} />

          {/* Feed List */}
          {isLoading ? (
            <Loading message="Loading latest travel notes…" />
          ) : error ? (
            <ErrorMessage message={error} onRetry={() => loadFeed(true)} />
          ) : posts.length === 0 ? (
            <Empty
              title="No posts found"
              description={
                authorFilter
                  ? 'This traveler has not posted any notes yet.'
                  : 'Be the first traveler to post a story above.'
              }
              action={
                authorFilter ? (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setAuthorFilter(null)}
                  >
                    Return to global feed
                  </button>
                ) : null
              }
            />
          ) : (
            <div className="posts-stream">
              {posts.map((post) => (
                <PostCard
                  key={post.post_id}
                  post={post}
                  onPostUpdated={handlePostUpdated}
                  onPostDeleted={handlePostDeleted}
                  onAuthorClick={handleAuthorClick}
                  onOpenDetail={handleOpenDetail}
                />
              ))}

              <Pagination
                nextCursor={nextCursor}
                isLoading={isLoadingMore}
                onLoadMore={() => loadFeed(false)}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
