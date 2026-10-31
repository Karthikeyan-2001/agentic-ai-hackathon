import { ChalkboardTeacher, Student } from '@phosphor-icons/react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ApiError, api } from '../api'
import { homeFor, useAuth } from '../auth'
import type { DemoAccount } from '../types'

export function LoginPage() {
  const { session, signIn } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [accounts, setAccounts] = useState<DemoAccount[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.demoAccounts().then(setAccounts).catch(() => setAccounts([]))
  }, [])

  if (session) return <Navigate to={homeFor(session.role)} replace />

  async function attempt(name: string, secret: string) {
    setBusy(true)
    setError('')
    try {
      const created = await signIn(name, secret)
      navigate(homeFor(created.role), { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Couldn't reach the server. Is it running?")
      setBusy(false)
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    void attempt(username, password)
  }

  return (
    <main className="mx-auto grid min-h-[100dvh] max-w-5xl content-center gap-10 px-4 py-10 md:grid-cols-[1fr_1fr] md:gap-16">
      <div>
        <Link to="/" className="text-lg font-bold tracking-tight">
          Differential
        </Link>
        <h1 className="mt-8 text-3xl font-semibold tracking-tight md:text-4xl">Sign in</h1>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div className="flex flex-col gap-2">
            <label htmlFor="username" className="text-sm font-semibold">
              Username
            </label>
            <input
              id="username"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="rounded-lg border border-line bg-card px-3 py-2.5 text-ink"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="password" className="text-sm font-semibold">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              aria-describedby={error ? 'login-error' : undefined}
              className="rounded-lg border border-line bg-card px-3 py-2.5 text-ink"
            />
            {error && (
              <p id="login-error" role="alert" className="text-sm text-bad">
                {error}
              </p>
            )}
          </div>
          <button
            type="submit"
            disabled={busy || !username || !password}
            className="w-full rounded-lg bg-accent px-5 py-2.5 font-semibold text-on-accent transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>

      <section aria-labelledby="demo-accounts" className="self-center">
        <h2 id="demo-accounts" className="font-semibold">
          Demo accounts
        </h2>
        <p className="mt-1 max-w-[50ch] text-sm text-mute">
          These are mock accounts for this local demo, not real security. Choose one to sign in straight away.
        </p>
        <ul className="mt-4 space-y-2">
          {accounts.map((account) => {
            const Icon = account.role === 'teacher' ? ChalkboardTeacher : Student
            return (
              <li key={account.username}>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    setUsername(account.username)
                    setPassword(account.password)
                    void attempt(account.username, account.password)
                  }}
                  className="flex w-full items-center gap-3 rounded-lg border border-line bg-card px-4 py-3 text-left transition hover:border-accent active:scale-[0.99] disabled:opacity-40"
                >
                  <Icon size={22} className="text-accent" aria-hidden="true" />
                  <span>
                    <span className="block font-semibold">{account.display_name}</span>
                    <span className="block font-mono text-xs text-mute">{account.username}</span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      </section>
    </main>
  )
}
