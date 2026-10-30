import { useState, useEffect, useCallback, useRef } from 'react';
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
  const { user } = useCurrentUser();

  // Navigation state: either { view: 'feed' } or { view: 'detail', postId }
  const [navigation, setNavigation] = useState({ view: 'feed', postId: null });

  // Filtering by specific author (null for global feed)
  const [authorFilter, setAuthorFilter] = useState(null);
  const [authorUser, setAuthorUser] = useState(null);

  const [posts, setPosts] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [initialError, setInitialError] = useState('');
  const [loadMoreError, setLoadMoreError] = useState('');
  const [postedNotice, setPostedNotice] = useState(false);

  // Track active fetch to cancel stale requests
  const activeControllerRef = useRef(null);

  const loadFeed = useCallback(async (reset = true) => {
    // Abort previous in-flight request
    if (activeControllerRef.current) {
      activeControllerRef.current.abort();
    }
    const controller = new AbortController();
    activeControllerRef.current = controller;

    if (reset) {
      setIsLoading(true);
      setInitialError('');
      setLoadMoreError('');
    } else {
      setIsLoadingMore(true);
      setLoadMoreError('');
    }

    try {
      const cursor = reset ? null : nextCursor;
      let data;

      if (authorFilter) {
        data = await getUserPosts(authorFilter, cursor, 20, { signal: controller.signal });
        if (data.user) {
          setAuthorUser(data.user);
        }
      } else {
        data = await getFeed(cursor, 20, { signal: controller.signal });
        setAuthorUser(null);
      }

      if (reset) {
        setPosts(data.items || []);
      } else {
        setPosts((prev) => [...prev, ...(data.items || [])]);
      }
      setNextCursor(data.next_cursor || null);
    } catch (err) {
      if (err.name !== 'AbortError') {
        if (reset) {
          setInitialError(err.message || 'Could not fetch posts.');
        } else {
          setLoadMoreError(err.message || 'Could not load older posts.');
        }
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
        setIsLoadingMore(false);
      }
    }
  }, [authorFilter, nextCursor]);

  useEffect(() => {
    loadFeed(true);
    return () => {
      if (activeControllerRef.current) {
        activeControllerRef.current.abort();
      }
    };
  }, [authorFilter]); // Only re-run when authorFilter changes

  const handlePostCreated = (newPost) => {
    // Only prepend if global feed or currently filtering by the author
    if (!authorFilter || (user && authorFilter === user.user_id)) {
      setPosts((prev) => [newPost, ...prev]);
      setPostedNotice(false);
    } else {
      setPostedNotice(true);
    }
  };

  const handlePostUpdated = (updated) => {
    setPosts((prev) =>
      prev.map((p) => (p.post_id === updated.post_id ? updated : p))
    );
  };

  const handlePostDeleted = (postId) => {
    setPosts((prev) => prev.filter((p) => p.post_id !== postId));
  };

  const handleCommentCountChange = (postId, delta) => {
    setPosts((prev) =>
      prev.map((p) =>
        p.post_id === postId
          ? { ...p, comment_count: Math.max(0, (p.comment_count || 0) + delta) }
          : p
      )
    );
  };

  const handleAuthorClick = (authorId) => {
    setAuthorFilter(authorId);
    setNavigation({ view: 'feed', postId: null });
  };

  const handleClearFilter = () => {
    setAuthorFilter(null);
    setAuthorUser(null);
    setPostedNotice(false);
  };

  const handleOpenDetail = (postId) => {
    setNavigation({ view: 'detail', postId });
  };

  const handleBackToFeed = () => {
    setNavigation({ view: 'feed', postId: null });
  };

  return (
    <div className="content-container">
      {/* Main Content Area */}
      {navigation.view === 'detail' ? (
        <PostDetail
          postId={navigation.postId}
          onBack={handleBackToFeed}
          onPostUpdated={handlePostUpdated}
          onPostDeleted={handlePostDeleted}
          onCommentCountChange={handleCommentCountChange}
        />
      ) : (
        <>
          {/* Feed Filter / Header */}
          <div className="feed-header-bar">
            {authorFilter ? (
              <div className="filter-pill">
                <span>
                  Posts by{' '}
                  <strong>
                    {authorUser
                      ? `${authorUser.display_name} (@${authorUser.username})`
                      : `traveler #${authorFilter}`}
                  </strong>
                </span>
                <button
                  type="button"
                  className="filter-clear-btn"
                  onClick={handleClearFilter}
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

          {postedNotice && (
            <div className="posted-notice-banner">
              <span>Your story was published!</span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleClearFilter}
              >
                View it in global feed
              </button>
            </div>
          )}

          {/* Composer */}
          <PostComposer onPostCreated={handlePostCreated} />

          {/* Feed Stream */}
          {isLoading ? (
            <Loading message="Loading latest travel notes…" />
          ) : initialError ? (
            <ErrorMessage message={initialError} onRetry={() => loadFeed(true)} />
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
                    onClick={handleClearFilter}
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
                  onCommentCountChange={handleCommentCountChange}
                />
              ))}

              {loadMoreError && (
                <div className="load-more-error-box">
                  <span className="error-text">⚠️ {loadMoreError}</span>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => loadFeed(false)}
                  >
                    Retry loading more
                  </button>
                </div>
              )}

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
