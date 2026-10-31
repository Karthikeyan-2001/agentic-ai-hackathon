import { ArrowLeft, ArrowRight, X } from '@phosphor-icons/react'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, isSignedIn, setAuthToken } from './api'
import { homeFor, useAuth } from './auth'
import type { AnswerDraft } from './components/QuestionCard'
import type { DemoStep, PublicQuestion } from './types'

// sessionStorage is per tab, like the sign-in, so only the tab that started the demo shows the guide.
const STORAGE_KEY = 'differential.demo.step'

function readStoredStep(): number | null {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY)
    return stored === null ? null : Number(stored)
  } catch {
    return null
  }
}

function writeStoredStep(step: number | null) {
  try {
    if (step === null) sessionStorage.removeItem(STORAGE_KEY)
    else sessionStorage.setItem(STORAGE_KEY, String(step))
  } catch {
    // The guide still works for this page view if storage is unavailable.
  }
}

interface DemoValue {
  steps: DemoStep[]
  stepIndex: number | null
  busy: boolean
  error: string
  start: () => Promise<void>
  goTo: (index: number) => Promise<void>
  stop: () => void
  prefillFor: (question: PublicQuestion) => AnswerDraft | null
}

const DemoContext = createContext<DemoValue | null>(null)

export function DemoProvider({ children }: { children: ReactNode }) {
  const { session, signIn } = useAuth()
  const navigate = useNavigate()
  const [steps, setSteps] = useState<DemoStep[]>([])
  const [stepIndex, setStepIndex] = useState<number | null>(readStoredStep)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (stepIndex === null || steps.length > 0) return
    api
      .demoScript()
      .then((script) => setSteps(script.steps))
      .catch(() => setError("Couldn't load the demo script."))
  }, [stepIndex, steps.length])

  const switchAccount = useCallback(
    async (username: string) => {
      const account = (await api.demoAccounts()).find((item) => item.username === username)
      if (!account) throw new Error(`Unknown demo account ${username}`)
      if (isSignedIn()) await api.logout().catch(() => undefined)
      const created = await signIn(account.username, account.password)
      navigate(homeFor(created.role))
    },
    [navigate, signIn],
  )

  const show = useCallback(
    async (script: DemoStep[], index: number) => {
      const step = script[index]
      if (step.account && step.account !== session?.username) {
        await switchAccount(step.account)
      } else if (step.account && session) {
        navigate(homeFor(session.role))
      } else if (!step.account) {
        navigate('/')
      }
      setStepIndex(index)
      writeStoredStep(index)
      if (step.anchor) {
        const anchor = step.anchor
        window.setTimeout(() => document.getElementById(anchor)?.scrollIntoView({ block: 'center' }), 100)
      } else {
        window.scrollTo({ top: 0, behavior: 'instant' })
      }
    },
    [navigate, session, switchAccount],
  )

  const run = useCallback(async (action: () => Promise<void>) => {
    setBusy(true)
    setError('')
    try {
      await action()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'That step failed.')
    } finally {
      setBusy(false)
    }
  }, [])

  const value = useMemo<DemoValue>(
    () => ({
      steps,
      stepIndex,
      busy,
      error,
      start: () =>
        run(async () => {
          const script = (await api.demoScript()).steps
          const teacher = (await api.demoAccounts()).find((item) => item.role === 'teacher')
          if (!teacher) throw new Error('The demo needs a teacher account.')
          // Reset without opening the teacher page, so the demo starts straight on the first student.
          if (isSignedIn()) await api.logout().catch(() => undefined)
          setAuthToken((await api.login(teacher.username, teacher.password)).token)
          await api.resetDemo()
          await api.logout().catch(() => undefined)
          setAuthToken(null)
          setSteps(script)
          const first = script[0]
          if (first.account) await switchAccount(first.account)
          setStepIndex(0)
          writeStoredStep(0)
          window.scrollTo({ top: 0, behavior: 'instant' })
        }),
      goTo: (index) => run(() => show(steps, index)),
      stop: () => {
        setStepIndex(null)
        writeStoredStep(null)
        setError('')
      },
      prefillFor: (question) => {
        if (stepIndex === null || !session) return null
        const answer = steps
          .filter((step) => step.account === session.username)
          .flatMap((step) => step.answers)
          .find((item) => item.question_id === question.id)
        const option = answer && question.options.find((item) => item.text === answer.option)
        if (!answer || !option) return null
        return { option_id: option.id, reasoning: answer.reasoning, confidence_tap: answer.confidence }
      },
    }),
    [steps, stepIndex, busy, error, run, session, show, switchAccount],
  )

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
}

export function useDemo(): DemoValue {
  const value = useContext(DemoContext)
  if (!value) throw new Error('useDemo must be used inside DemoProvider')
  return value
}

export function StartDemoButton({ className = '' }: { className?: string }) {
  const { start, busy, error } = useDemo()
  return (
    <>
      <button
        type="button"
        disabled={busy}
        onClick={() => void start()}
        title="Resets the four demo students, then walks through every feature with the answers filled in."
        className={`inline-flex items-center justify-center gap-2 rounded-lg border border-accent px-5 py-3 font-semibold whitespace-nowrap text-accent transition active:scale-[0.98] disabled:opacity-40 ${className}`}
      >
        {busy ? 'Starting…' : 'Start guided demo'}
      </button>
      {error && (
        <p role="alert" className="text-sm text-bad">
          {error}
        </p>
      )}
    </>
  )
}

export function DemoBar() {
  const { steps, stepIndex, busy, error, goTo, stop } = useDemo()
  if (stepIndex === null || steps.length === 0) return null
  const step = steps[stepIndex]
  if (!step) return null
  const last = stepIndex === steps.length - 1

  return (
    <>
      <div className="h-40 sm:h-28" aria-hidden="true" />
      <section
        aria-label="Guided demo"
        className="fixed inset-x-0 bottom-0 z-50 border-t-2 border-accent bg-card px-4 py-3 shadow-[0_-6px_18px_rgb(0_0_0/0.18)]"
      >
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-6 gap-y-2">
          <div className="min-w-0 flex-1 basis-80">
            <p className="text-xs font-semibold tracking-wide text-accent uppercase">
              Step {stepIndex + 1} of {steps.length}
            </p>
            <h2 className="font-semibold">{step.title}</h2>
            <p className="max-w-[90ch] text-sm text-mute">{step.note}</p>
            {error && (
              <p role="alert" className="mt-1 text-sm text-bad">
                {error}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={busy || stepIndex === 0}
              onClick={() => void goTo(stepIndex - 1)}
              className="inline-flex items-center gap-1 rounded-md border border-line px-3 py-2 text-sm font-semibold hover:border-mute active:scale-[0.98] disabled:opacity-40"
            >
              <ArrowLeft size={16} aria-hidden="true" />
              Back
            </button>
            {last ? (
              <button
                type="button"
                onClick={stop}
                className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-on-accent active:scale-[0.98]"
              >
                Finish
              </button>
            ) : (
              <button
                type="button"
                disabled={busy}
                onClick={() => void goTo(stepIndex + 1)}
                className="inline-flex items-center gap-1 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-on-accent active:scale-[0.98] disabled:opacity-40"
              >
                {busy ? 'Switching…' : 'Next step'}
                <ArrowRight size={16} weight="bold" aria-hidden="true" />
              </button>
            )}
            <button
              type="button"
              aria-label="Leave the guided demo"
              title="Leave the guided demo"
              onClick={stop}
              className="rounded-md border border-line p-2 hover:border-mute active:scale-[0.98]"
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        </div>
      </section>
    </>
  )
}
