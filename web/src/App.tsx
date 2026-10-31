import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import { StudentPage } from './pages/StudentPage'
import { TeacherPage } from './pages/TeacherPage'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-semibold ${isActive ? 'bg-accent text-white' : 'text-ink hover:bg-none'}`

export default function App() {
  return (
    <BrowserRouter>
      <header className="border-b border-line bg-card">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div>
            <p className="text-lg font-bold">Differential</p>
            <p className="text-xs text-mute">A Class 10 physics tutor that diagnoses reasoning, not just answers</p>
          </div>
          <nav className="flex gap-1">
            <NavLink to="/" end className={navClass}>
              Student
            </NavLink>
            <NavLink to="/teacher" className={navClass}>
              Teacher
            </NavLink>
          </nav>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<StudentPage />} />
          <Route path="/teacher" element={<TeacherPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
