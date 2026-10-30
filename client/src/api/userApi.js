import { apiRequest } from './client.js'

// Auth
export const register = (fields) => apiRequest('/api/auth/register', { method: 'POST', body: fields })
export const login = (identifier, password) =>
  apiRequest('/api/auth/login', { method: 'POST', body: { identifier, password } })
export const logout = () => apiRequest('/api/auth/logout', { method: 'POST' })

// Profiles
export const getMe = () => apiRequest('/api/users/me')
export const updateMe = (fields) => apiRequest('/api/users/me', { method: 'PATCH', body: fields })
export const getUser = (userId) => apiRequest(`/api/users/${userId}`)
export const getUserByUsername = (username) =>
  apiRequest(`/api/users/by-username/${encodeURIComponent(username)}`)

// Follows
export const followUser = (userId) => apiRequest(`/api/users/${userId}/follow`, { method: 'POST' })
export const unfollowUser = (userId) => apiRequest(`/api/users/${userId}/follow`, { method: 'DELETE' })
export const getFollowers = (userId, page = 1, limit = 20) =>
  apiRequest(`/api/users/${userId}/followers?page=${page}&limit=${limit}`)
export const getFollowing = (userId, page = 1, limit = 20) =>
  apiRequest(`/api/users/${userId}/following?page=${page}&limit=${limit}`)
