import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'

import {
  api,
  refreshAccessToken,
  request,
  setAuthFailureHandler,
  setTokenListener,
  tokenStore,
} from '@/services/api/client'
import type { TokenOut, UserOut } from '@/services/api/types'

type Status = 'loading' | 'authenticated' | 'anonymous'

interface AuthContextValue {
  status: Status
  user: UserOut | null
  /** Where to go after an intentional sign-out (no "next" back-link). */
  signOutTarget: string | null
  login: (email: string, password: string) => Promise<UserOut>
  logout: () => Promise<void>
  /** End the local session (after logout or account deletion) and go to `target`. */
  endSession: (target?: string) => void
  setUser: (user: UserOut | null) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function loginPath(next: string): string {
  return next && next !== '/' && !next.startsWith('/login') ? `/login?next=${encodeURIComponent(next)}` : '/login'
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>('loading')
  const [user, setUserState] = useState<UserOut | null>(null)
  const [signOutTarget, setSignOutTarget] = useState<string | null>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const locationRef = useRef(location)
  useEffect(() => {
    locationRef.current = location
  }, [location])

  const setUser = useCallback((u: UserOut | null) => {
    setUserState(u)
    setStatus(u ? 'authenticated' : 'anonymous')
    if (u) setSignOutTarget(null)
  }, [])

  const endSession = useCallback((target = '/login') => {
    tokenStore.set(null)
    setSignOutTarget(target)
    setUserState(null)
    setStatus('anonymous')
    queryClient.clear()
  }, [queryClient])

  useEffect(() => {
    setTokenListener((tok) => {
      if (tok) setUser(tok.user as UserOut)
    })
    setAuthFailureHandler(() => {
      tokenStore.set(null)
      setUser(null)
      queryClient.clear()
      const here = locationRef.current
      navigate(loginPath(here.pathname + here.search), { replace: true })
    })
    let cancelled = false
    // Restore the session from the httpOnly refresh cookie, if any.
    void refreshAccessToken().then((ok) => {
      if (!cancelled && !ok) setUser(null)
    })
    return () => {
      cancelled = true
    }
  }, [navigate, queryClient, setUser])

  const login = useCallback(async (email: string, password: string) => {
    const tok = await api.post<TokenOut>('/auth/login', { email, password }, { anonymous: true })
    tokenStore.set(tok.access_token)
    setUser(tok.user)
    return tok.user
  }, [setUser])

  const logout = useCallback(async () => {
    try {
      await request('/auth/logout', { method: 'POST' })
    } catch {
      /* already signed out */
    }
    endSession('/login')
  }, [endSession])

  const value = useMemo(
    () => ({ status, user, signOutTarget, login, logout, endSession, setUser }),
    [status, user, signOutTarget, login, logout, endSession, setUser],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
