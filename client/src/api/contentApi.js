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
}

// =========================================================
// FEED & POSTS
// =========================================================

export async function getFeed(cursor = null, limit = 20) {
  const params = new URLSearchParams();
  if (limit) params.set('limit', limit);
  if (cursor) params.set('cursor', cursor);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request(`/feed${qs}`, { method: 'GET' });
}

export async function getPost(postId) {
  return request(`/posts/${postId}`, { method: 'GET' });
}

export async function createPost(postData) {
  return request('/posts', {
    method: 'POST',
    body: postData,
  });
}

export async function updatePost(postId, postData) {
  return request(`/posts/${postId}`, {
    method: 'PATCH',
    body: postData,
  });
}

export async function deletePost(postId) {
  return request(`/posts/${postId}`, {
    method: 'DELETE',
  });
}

export async function getUserPosts(userId, cursor = null, limit = 20) {
  const params = new URLSearchParams();
  if (limit) params.set('limit', limit);
  if (cursor) params.set('cursor', cursor);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request(`/users/${userId}/posts${qs}`, { method: 'GET' });
}

// =========================================================
// COMMENTS
// =========================================================

export async function getComments(postId) {
  return request(`/posts/${postId}/comments`, { method: 'GET' });
}

export async function createComment(postId, commentData) {
  return request(`/posts/${postId}/comments`, {
    method: 'POST',
    body: commentData,
  });
}

export async function updateComment(commentId, commentData) {
  return request(`/comments/${commentId}`, {
    method: 'PATCH',
    body: commentData,
  });
}

export async function deleteComment(commentId) {
  return request(`/comments/${commentId}`, {
    method: 'DELETE',
  });
}

// =========================================================
// REPLIES
// =========================================================

export async function getReplies(commentId) {
  return request(`/comments/${commentId}/replies`, { method: 'GET' });
}

export async function createReply(commentId, replyData) {
  return request(`/comments/${commentId}/replies`, {
    method: 'POST',
    body: replyData,
  });
}

export async function updateReply(replyId, replyData) {
  return request(`/replies/${replyId}`, {
    method: 'PATCH',
    body: replyData,
  });
}

export async function deleteReply(replyId) {
  return request(`/replies/${replyId}`, {
    method: 'DELETE',
  });
}
