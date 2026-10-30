import { useAuth } from '../context/AuthContext.js'

export function getAuthHeaders() {
  return {}
}

export function useCurrentUser() {
  const { user, loading } = useAuth()
  return {
    user,
    isLoggedIn: Boolean(user),
    loading,
  }
}
