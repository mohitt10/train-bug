/**
 * Content API Client
 * 
 * The ONLY file allowed to call fetch() for content endpoints.
 * All requests route through a single request() helper that prefixes /api,
 * attaches auth headers via authBridge, and normalizes errors.
 */

import { getAuthHeaders } from './authBridge';

const API_BASE = '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const authHeaders = getAuthHeaders();

  const headers = {
    'Content-Type': 'application/json',
    ...authHeaders,
    ...options.headers,
  };

  const config = {
    ...options,
    headers,
  };

  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  try {
    const response = await fetch(url, config);

    if (response.status === 204) {
      return null;
    }

    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      try {
        data = await response.json();
      } catch {
        data = null;
      }
    }

    if (!response.ok) {
      const errorObj = data?.error || {};
      const normalizedError = new Error(
        errorObj.message || `Request failed with HTTP ${response.status}`
      );
      normalizedError.status = response.status;
      normalizedError.code = errorObj.code || 'UNKNOWN_ERROR';
      throw normalizedError;
    }

    return data;
  } catch (err) {
    if (err.name === 'AbortError') {
      throw err;
    }
    throw err;
  }
}

// =========================================================
// FEED & POSTS
// =========================================================

export async function getFeed(cursor = null, limit = 20, options = {}) {
  const params = new URLSearchParams();
  if (limit) params.set('limit', limit);
  if (cursor) params.set('cursor', cursor);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request(`/feed${qs}`, { method: 'GET', ...options });
}

export async function getPost(postId, options = {}) {
  return request(`/posts/${postId}`, { method: 'GET', ...options });
}

export async function createPost(postData, options = {}) {
  return request('/posts', {
    method: 'POST',
    body: postData,
    ...options,
  });
}

export async function updatePost(postId, postData, options = {}) {
  return request(`/posts/${postId}`, {
    method: 'PATCH',
    body: postData,
    ...options,
  });
}

export async function deletePost(postId, options = {}) {
  return request(`/posts/${postId}`, {
    method: 'DELETE',
    ...options,
  });
}

export async function getUserPosts(userId, cursor = null, limit = 20, options = {}) {
  const params = new URLSearchParams();
  if (limit) params.set('limit', limit);
  if (cursor) params.set('cursor', cursor);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request(`/users/${userId}/posts${qs}`, { method: 'GET', ...options });
}

// =========================================================
// COMMENTS
// =========================================================

export async function getComments(postId, options = {}) {
  return request(`/posts/${postId}/comments`, { method: 'GET', ...options });
}

export async function createComment(postId, commentData, options = {}) {
  return request(`/posts/${postId}/comments`, {
    method: 'POST',
    body: commentData,
    ...options,
  });
}

export async function updateComment(commentId, commentData, options = {}) {
  return request(`/comments/${commentId}`, {
    method: 'PATCH',
    body: commentData,
    ...options,
  });
}

export async function deleteComment(commentId, options = {}) {
  return request(`/comments/${commentId}`, {
    method: 'DELETE',
    ...options,
  });
}

// =========================================================
// REPLIES
// =========================================================

export async function getReplies(commentId, options = {}) {
  return request(`/comments/${commentId}/replies`, { method: 'GET', ...options });
}

export async function createReply(commentId, replyData, options = {}) {
  return request(`/comments/${commentId}/replies`, {
    method: 'POST',
    body: replyData,
    ...options,
  });
}

export async function updateReply(replyId, replyData, options = {}) {
  return request(`/replies/${replyId}`, {
    method: 'PATCH',
    body: replyData,
    ...options,
  });
}

export async function deleteReply(replyId, options = {}) {
  return request(`/replies/${replyId}`, {
    method: 'DELETE',
    ...options,
  });
}
