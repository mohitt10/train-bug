import { createContext, useContext } from 'react'

export const AuthContext = createContext(null)

// Phases 3 and 4: const { user } = useAuth()  ->  user.user_id, user.username, ...
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
