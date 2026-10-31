import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, api, percent } from '../api'
import { useAuth } from '../auth'
import { ConceptGraph } from '../components/ConceptGraph'
import { QuestionCard, type AnswerDraft } from '../components/QuestionCard'
import { ResultCard } from '../components/ResultCard'
import { ReviewsPanel } from '../components/ReviewsPanel'
import { ThinkingPanel } from '../components/ThinkingPanel'
import { useDemo } from '../demo'
import type { AnswerResponse, NextResponse, StudentState } from '../types'

function DiagnosticDone({ state }: { state: StudentState }) {
  const assessed = state.concepts.filter((concept) => concept.assessed && concept.has_questions)
  const weakest = [...assessed].sort((first, second) => first.mastery - second.mastery)[0]
  return (
    <p role="status" className="rounded-md bg-accent-soft px-4 py-3 text-sm">
      <span className="font-semibold">Diagnostic complete.</span> All {state.diagnostic_length} questions are answered.
      {weakest && ` The weakest concept so far is ${weakest.name}, at ${percent(weakest.mastery)}.`}
    </p>
  )
}

export function StudentPage() {
  const { session } = useAuth()
  const { prefillFor } = useDemo()
  const studentId = session?.student_id ?? ''
  const [next, setNext] = useState<NextResponse | null>(null)
  const [state, setState] = useState<StudentState | null>(null)
  const [result, setResult] = useState<AnswerResponse | null>(null)
  const [formVersion, setFormVersion] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [diagnosticDone, setDiagnosticDone] = useState(false)
  const submitting = useRef(false)
  const view = useRef({ questionId: '', showingResult: false, busy: false })
  view.current = { questionId: next?.question?.id ?? '', showingResult: result !== null, busy }

  const load = useCallback(async () => {
    setError('')
    setBusy(true)
    try {
      const [nextResponse, stateResponse] = await Promise.all([api.next(studentId), api.state(studentId)])
      setNext(nextResponse)
      setState(stateResponse)
      setResult(null)
      setDiagnosticDone(false)
      setFormVersion((version) => version + 1)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }, [studentId])

  useEffect(() => {
    void load()
  }, [load])

  // The teacher can jump the clock or reset the demo from another window, so catch up when this one regains focus.
  useEffect(() => {
    async function refresh() {
      if (view.current.busy) return
      const [nextResponse, stateResponse] = await Promise.all([api.next(studentId), api.state(studentId)])
      setState(stateResponse)
      const changed = (nextResponse.question?.id ?? '') !== view.current.questionId
      if (changed && !view.current.showingResult) {
        setNext(nextResponse)
        setFormVersion((version) => version + 1)
      }
    }
    const onFocus = () => void refresh().catch(() => undefined)
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [studentId])

  async function submit(draft: AnswerDraft) {
    // A ref blocks a second click before React has rerendered with the disabled button.
    if (!next?.question || busy || submitting.current) return
    submitting.current = true
    setBusy(true)
    setError('')
    try {
      const response = await api.answer(studentId, { question_id: next.question.id, ...draft })
      setResult(response)
      const stateResponse = await api.state(studentId)
      setDiagnosticDone(state?.diagnostic_complete === false && stateResponse.diagnostic_complete)
      setState(stateResponse)
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        await load()
      } else {
        setError(caught instanceof Error ? caught.message : 'Something went wrong.')
      }
    } finally {
      submitting.current = false
      setBusy(false)
    }
  }

  const prefill = next?.question ? prefillFor(next.question) : null
  const progress =
    state && !state.diagnostic_complete ? `Diagnostic: question ${state.answer_count + 1} of ${state.diagnostic_length}` : undefined

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {error && (
        <p role="alert" className="mb-4 rounded-md bg-bad-soft px-4 py-3 text-bad">
          {error}
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="space-y-4">
          {diagnosticDone && state && <DiagnosticDone state={state} />}
          {result ? (
            <ResultCard result={result} loading={busy} onNext={() => void load()} />
          ) : next?.question ? (
            <QuestionCard
              key={`${formVersion}-${prefill ? 'filled' : 'empty'}`}
              question={next.question}
              submitting={busy}
              prefill={prefill}
              progress={progress}
              onSubmit={submit}
            />
          ) : (
            next && (
              <section className="rounded-lg border border-line bg-card p-6">
                <h2 className="text-xl font-semibold">All caught up</h2>
                <p className="mt-2 text-mute">Nothing needs practice right now. Check back when a review comes due.</p>
              </section>
            )
          )}
          {state && <ReviewsPanel state={state} />}
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
