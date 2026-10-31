import { useCallback, useEffect, useState } from 'react'
import { ApiError, api } from '../api'
import { ConceptGraph } from '../components/ConceptGraph'
import { QuestionCard, type AnswerDraft } from '../components/QuestionCard'
import { ResultCard } from '../components/ResultCard'
import { ReviewsPanel } from '../components/ReviewsPanel'
import { ThinkingPanel } from '../components/ThinkingPanel'
import type { AnswerResponse, NextResponse, Student, StudentState } from '../types'

export function StudentPage() {
  const [students, setStudents] = useState<Student[]>([])
  const [studentId, setStudentId] = useState('')
  const [next, setNext] = useState<NextResponse | null>(null)
  const [state, setState] = useState<StudentState | null>(null)
  const [result, setResult] = useState<AnswerResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async (id: string) => {
    setError('')
    setBusy(true)
    try {
      const [nextResponse, stateResponse] = await Promise.all([api.next(id), api.state(id)])
      setNext(nextResponse)
      setState(stateResponse)
      setResult(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }, [])

  const loadStudents = useCallback(async () => {
    const list = await api.students()
    setStudents(list)
    setStudentId((current) => current || list[0]?.id || '')
  }, [])

  useEffect(() => {
    loadStudents().catch((caught) => setError(caught instanceof Error ? caught.message : 'Something went wrong.'))
  }, [loadStudents])

  useEffect(() => {
    if (studentId) void load(studentId)
  }, [studentId, load])

  async function submit(draft: AnswerDraft) {
    if (!next?.question || busy) return
    setBusy(true)
    setError('')
    try {
      const response = await api.answer(studentId, { question_id: next.question.id, ...draft })
      setResult(response)
      setState(await api.state(studentId))
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        await load(studentId)
      } else {
        setError(caught instanceof Error ? caught.message : 'Something went wrong.')
      }
    } finally {
      setBusy(false)
    }
  }

  async function jump() {
    setBusy(true)
    try {
      await api.advanceClock(7)
    } finally {
      setBusy(false)
    }
    await load(studentId)
  }

  async function resetDemo() {
    setBusy(true)
    try {
      await api.resetDemo()
    } finally {
      setBusy(false)
    }
    await load(studentId)
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm font-semibold">
          Student
          <select
            value={studentId}
            onChange={(event) => setStudentId(event.target.value)}
            className="rounded-md border border-line bg-card px-3 py-2 font-normal"
          >
            {students.map((student) => (
              <option key={student.id} value={student.id}>
                {student.name}
                {student.diagnostic_complete ? '' : ' (diagnostic)'}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={resetDemo}
          disabled={busy}
          className="rounded-md border border-line bg-card px-3 py-2 text-sm hover:border-mute disabled:opacity-40"
        >
          Reset demo
        </button>
      </div>

      {error && (
        <p role="alert" className="mt-4 rounded-md bg-bad-soft px-4 py-3 text-bad">
          {error}
        </p>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="space-y-4">
          {result ? (
            <ResultCard result={result} loading={busy} onNext={() => void load(studentId)} />
          ) : next?.question ? (
            <QuestionCard key={next.question.id} question={next.question} submitting={busy} onSubmit={submit} />
          ) : (
            next && (
              <section className="rounded-lg border border-line bg-card p-6">
                <h2 className="text-xl font-semibold">All caught up</h2>
                <p className="mt-2 text-mute">Nothing needs practice right now. Jump ahead to see reviews come due.</p>
              </section>
            )
          )}
          {state && <ReviewsPanel state={state} busy={busy} onJump={jump} />}
        </div>
        <ThinkingPanel next={next} result={result} />
      </div>
      {state && (
        <div className="mt-4">
          <ConceptGraph concepts={state.concepts} />
        </div>
      )}
    </div>
  )
}
