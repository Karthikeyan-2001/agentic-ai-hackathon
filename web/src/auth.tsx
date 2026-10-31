import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { api, setAuthToken, setSignedOutHandler } from './api'
import type { Role, Session } from './types'

// sessionStorage is per tab, so a teacher and a student can stay signed in side by side during the demo.
const STORAGE_KEY = 'differential.session'

function readStoredSession(): Session | null {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY)
    return stored ? (JSON.parse(stored) as Session) : null
  } catch {
    return null
  }
}

function writeStoredSession(session: Session | null) {
  try {
    if (session) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    else sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // The session still works for this page view if storage is unavailable.
  }
}

interface AuthValue {
  session: Session | null
  signIn: (username: string, password: string) => Promise<Session>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

export const homeFor = (role: Role) => (role === 'teacher' ? '/teacher' : '/student')

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(() => {
    const stored = readStoredSession()
    setAuthToken(stored?.token ?? null)
    return stored
  })

  const clear = useCallback(() => {
    setAuthToken(null)
    writeStoredSession(null)
    setSession(null)
  }, [])

  setSignedOutHandler(clear)

  const value = useMemo<AuthValue>(
    () => ({
      session,
      signIn: async (username, password) => {
        const created = await api.login(username, password)
        setAuthToken(created.token)
        writeStoredSession(created)
        setSession(created)
        return created
      },
      signOut: async () => {
        await api.logout().catch(() => undefined)
        clear()
      },
    }),
    [session, clear],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}

export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { session } = useAuth()
  if (!session) return <Navigate to="/login" replace />
  if (session.role !== role) return <Navigate to={homeFor(session.role)} replace />
  return children
}
