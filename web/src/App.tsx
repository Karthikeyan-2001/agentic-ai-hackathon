import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, RequireRole, useAuth } from './auth'
import { DemoBar, DemoProvider } from './demo'
import { LandingPage } from './pages/LandingPage'
import { LoginPage } from './pages/LoginPage'
import { StudentPage } from './pages/StudentPage'
import { TeacherPage } from './pages/TeacherPage'
import type { ReactNode } from 'react'

function AppShell({ children }: { children: ReactNode }) {
  const { session, signOut } = useAuth()
  return (
    <>
      <header className="border-b border-line bg-card">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link to="/" className="text-lg font-bold tracking-tight">
            Differential
          </Link>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-mute">Signed in as {session?.display_name}</span>
            <button
              type="button"
              onClick={() => void signOut()}
              className="rounded-md border border-line px-3 py-1.5 font-semibold hover:border-mute active:scale-[0.98]"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main>{children}</main>
    </>
  )
}

function StudentRoute() {
  const { session } = useAuth()
  // The guided demo moves straight from one student to the next, so each one gets a fresh page.
  return <StudentPage key={session?.student_id} />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <DemoProvider>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/student"
              element={
                <RequireRole role="student">
                  <AppShell>
                    <StudentRoute />
                  </AppShell>
                </RequireRole>
              }
            />
            <Route
              path="/teacher"
              element={
                <RequireRole role="teacher">
                  <AppShell>
                    <TeacherPage />
                  </AppShell>
                </RequireRole>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <DemoBar />
        </DemoProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
