import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCurrentUser } from '../../api/authBridge';
import { createPost } from '../../api/contentApi';

export function PostComposer({ onPostCreated }) {
  const { user, isLoggedIn } = useCurrentUser();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [location, setLocation] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmedContent = content.trim();

    if (!trimmedContent) {
      setError('Post content is required.');
      return;
    }

    if (title.trim().length > 200) {
      setError('Title must not exceed 200 characters.');
      return;
    }

    if (location.trim().length > 100) {
      setError('Location must not exceed 100 characters.');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const payload = {
        content: trimmedContent,
        title: title.trim() || null,
        location: location.trim() || null,
      };

      const newPost = await createPost(payload);
      setTitle('');
      setContent('');
      setLocation('');
      if (onPostCreated) {
        onPostCreated(newPost);
      }
    } catch (err) {
      setError(err.message || 'Failed to publish post.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="card composer-card login-cta">
        <p><Link to="/login">Log in</Link> to share a travel note.</p>
      </div>
    );
  }

  return (
    <section className="card composer-card" aria-label="Compose New Post">
      <div className="composer-header">
        <h3>Share a Travel Note</h3>
        <span className="posting-as">Posting as <strong>{user?.display_name || user?.username}</strong></span>
      </div>

      <form onSubmit={handleSubmit} className="composer-form">
        <div className="form-group">
          <input
            type="text"
            className="form-input"
            placeholder="Title (optional, max 200 chars)"
            maxLength={200}
            value={title}
            disabled={isSubmitting}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        <div className="form-group">
          <textarea
            className="form-textarea"
            rows={4}
            placeholder="Write your travel story, route notes, or itinerary insights… (required)"
            value={content}
            disabled={isSubmitting}
            onChange={(e) => {
              setContent(e.target.value);
              if (error) setError('');
            }}
          />
        </div>

        <div className="form-group">
          <input
            type="text"
            className="form-input form-input-sm"
            placeholder="📍 Location (e.g. Tamhini Ghat, Shimla Railway, Pondicherry)"
            maxLength={100}
            value={location}
            disabled={isSubmitting}
            onChange={(e) => setLocation(e.target.value)}
          />
        </div>

        {error && <div className="card-error-inline">{error}</div>}

        <div className="composer-actions">
          <span className="counter counter-muted">{content.length} chars</span>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isSubmitting || !content.trim()}
          >
            {isSubmitting ? 'Publishing…' : 'Publish Note'}
          </button>
        </div>
      </form>
    </section>
  );
}
