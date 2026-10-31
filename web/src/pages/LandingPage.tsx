import {
  ArrowRight,
  Brain,
  CalendarCheck,
  ChalkboardTeacher,
  Exam,
  Graph,
  MagnifyingGlass,
  Sliders,
  type Icon,
} from '@phosphor-icons/react'
import { useEffect, useRef, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { homeFor, useAuth } from '../auth'
import { DiagnosisDemo } from '../components/landing/DiagnosisDemo'
import { HeroGraph } from '../components/landing/HeroGraph'

const STEPS = [
  { name: 'Check', owner: 'Code', detail: 'Marks the answer right or wrong.' },
  { name: 'Diagnose', owner: 'Local LLM', detail: 'Reads the reasoning and names what it shows.' },
  { name: 'Validate', owner: 'Code', detail: "Rejects it unless the quote is in the student's own words." },
  { name: 'Update', owner: 'Code', detail: 'Moves mastery, misconceptions, reviews and difficulty.' },
  { name: 'Decide', owner: 'Code', detail: 'Picks the question that best separates what is left.' },
]

interface Feature {
  name: string
  detail: string
  icon: Icon
  span: string
  tone: string
}

const FEATURES: Feature[] = [
  {
    name: 'Misconceptions from reasoning',
    detail: 'The tutor judges the explanation, so two identical wrong answers can get two different diagnoses.',
    icon: MagnifyingGlass,
    span: 'lg:col-span-3',
    tone: 'bg-accent text-on-accent',
  },
  {
    name: 'A learner model for every answer',
    detail: 'Mastery per concept and a probability per misconception update after each answer.',
    icon: Brain,
    span: 'lg:col-span-3',
    tone: 'bg-accent-soft',
  },
  {
    name: 'Diagnostic test',
    detail: 'Eight adaptive questions, each with reasoning and a confidence tap.',
    icon: Exam,
    span: 'lg:col-span-2',
    tone: 'bg-card',
  },
  {
    name: 'Concept graph',
    detail: 'Class 10 physics mapped into 29 linked concepts, with Electricity covered in depth.',
    icon: Graph,
    span: 'lg:col-span-2',
    tone: 'bg-card',
  },
  {
    name: 'Spaced repetition',
    detail: 'A forgetting curve brings back fading concepts, and rechecks cleared misconceptions.',
    icon: CalendarCheck,
    span: 'lg:col-span-2',
    tone: 'bg-card',
  },
  {
    name: 'Targeted questions, calibrated difficulty',
    detail: 'Questions target weak concepts. Code checks generated answers, and Elo ratings adjust difficulty from class results.',
    icon: Sliders,
    span: 'lg:col-span-4',
    tone: 'bg-accent-soft',
  },
  {
    name: 'Teacher dashboard',
    detail: 'Class-wide gaps, shared misconceptions and root causes in one view.',
    icon: ChalkboardTeacher,
    span: 'lg:col-span-2',
    tone: 'bg-card',
  },
]

const CLASS_GAPS = [
  { name: 'Current in a series circuit', value: 23, detail: '20 of 28 below 40%' },
  { name: 'Electrical energy', value: 31, detail: '10 of 14 below 40%' },
  { name: 'Potential difference', value: 31, detail: '6 of 12 below 40%' },
  { name: 'Electric power', value: 35, detail: '17 of 30 below 40%' },
]

function Reveal({ children, className = '' }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const element = ref.current
    if (!element) return
    if (typeof IntersectionObserver === 'undefined') {
      element.classList.add('is-visible')
      return
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          element.classList.add('is-visible')
          observer.disconnect()
        }
      },
      { threshold: 0.12 },
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={ref} className={`reveal ${className}`}>
      {children}
    </div>
  )
}

function PrimaryAction() {
  const { session } = useAuth()
  const target = session ? homeFor(session.role) : '/login'
  return (
    <Link
      to={target}
      className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-3 font-semibold whitespace-nowrap text-on-accent transition hover:gap-3 active:scale-[0.98]"
    >
      {session ? 'Open the app' : 'Sign in'}
      <ArrowRight size={18} weight="bold" aria-hidden="true" />
    </Link>
  )
}

export function LandingPage() {
  const { session } = useAuth()

  return (
    <div className="min-h-[100dvh] overflow-x-clip">
      <header className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4">
        <span className="text-lg font-bold tracking-tight">Differential</span>
        <nav aria-label="Main" className="flex items-center gap-5 text-sm font-medium">
          <a href="#diagnosis" className="hover:text-accent max-sm:hidden">
            See a diagnosis
          </a>
          <a href="#how" className="hover:text-accent max-sm:hidden">
            How it works
          </a>
          <Link to={session ? homeFor(session.role) : '/login'} className="font-semibold text-accent">
            {session ? 'Open the app' : 'Sign in'}
          </Link>
        </nav>
      </header>

      <main>
        <section className="mx-auto grid max-w-7xl items-center gap-10 px-4 pt-10 pb-16 lg:grid-cols-[5fr_6fr] lg:gap-14 lg:pt-16 lg:pb-24">
          <div>
            <h1 className="text-4xl leading-[1.05] font-semibold tracking-tighter text-balance md:text-5xl lg:text-6xl">
              Your tutor knows the answer was wrong. Ours knows why.
            </h1>
            <p className="mt-6 max-w-[46ch] text-lg leading-relaxed text-mute">
              A Class 10 physics tutor that reads a student's reasoning, names the misconception, then asks the question
              that tests it.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-5">
              <PrimaryAction />
              <a href="#diagnosis" className="font-semibold hover:text-accent">
                See a diagnosis
              </a>
            </div>
          </div>
          <HeroGraph />
        </section>

        <section id="diagnosis" className="mx-auto max-w-7xl scroll-mt-6 px-4 py-16 lg:py-24">
          <Reveal>
            <h2 className="max-w-[20ch] text-3xl font-semibold tracking-tight md:text-4xl">
              One question. Three students. Three different problems.
            </h2>
            <p className="mt-4 max-w-[60ch] leading-relaxed text-mute">
              A tutor that only checks the final answer treats A and B the same, and gives C full marks. Choose a student
              to see what changes.
            </p>
            <div className="mt-8">
              <DiagnosisDemo />
            </div>
            <p className="mt-3 text-sm text-mute">Recorded from a real demo run on the local model.</p>
          </Reveal>
        </section>

        <section id="how" className="mx-auto max-w-7xl scroll-mt-6 px-4 py-16 lg:py-24">
          <Reveal>
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">The LLM interprets. The code decides.</h2>
            <p className="mt-4 max-w-[60ch] leading-relaxed text-mute">
              The model never sets a score, marks an answer or chooses a question, so every number can be explained.
            </p>
            <ol className="mt-10 grid gap-x-6 gap-y-8 md:grid-cols-5">
              {STEPS.map((step) => {
                const isModel = step.owner !== 'Code'
                return (
                  <li key={step.name} className={`border-t-2 pt-4 ${isModel ? 'border-accent' : 'border-line'}`}>
                    <p className={`text-sm font-semibold ${isModel ? 'text-accent' : 'text-mute'}`}>{step.owner}</p>
                    <h3 className="mt-1 text-xl font-semibold tracking-tight">{step.name}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-mute">{step.detail}</p>
                  </li>
                )
              })}
            </ol>
          </Reveal>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-16 lg:py-24">
          <Reveal>
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
              Everything the brief asked for, working together
            </h2>
            <ul className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-6">
              {FEATURES.map((feature) => (
                <li
                  key={feature.name}
                  className={`rounded-2xl border border-line p-6 transition hover:-translate-y-0.5 ${feature.span} ${feature.tone}`}
                >
                  <feature.icon size={28} aria-hidden="true" />
                  <h3 className="mt-4 text-lg font-semibold tracking-tight">{feature.name}</h3>
                  <p className="mt-2 text-sm leading-relaxed opacity-85">{feature.detail}</p>
                </li>
              ))}
            </ul>
          </Reveal>
        </section>

        <section className="mx-auto grid max-w-7xl items-start gap-10 px-4 py-16 lg:grid-cols-[2fr_3fr] lg:gap-16 lg:py-24">
          <Reveal>
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
              Teachers see the gap, not just the grades
            </h2>
            <p className="mt-4 max-w-[50ch] leading-relaxed text-mute">
              The dashboard ranks the weakest concepts, groups students who share a misconception, and traces low scores
              back to the prerequisite behind them.
            </p>
          </Reveal>
          <Reveal>
            <figure>
              <ul className="space-y-5">
                {CLASS_GAPS.map((gap) => (
                  <li key={gap.name}>
                    <div className="flex flex-wrap items-baseline justify-between gap-x-4">
                      <span className="font-medium">{gap.name}</span>
                      <span className="text-sm text-mute tabular-nums">
                        <span className="text-base font-semibold text-ink">{gap.value}%</span> average, {gap.detail}
                      </span>
                    </div>
                    <div
                      className="mt-2 h-2.5 rounded-full bg-accent"
                      style={{ width: `${gap.value * 2}%` }}
                      aria-hidden="true"
                    />
                  </li>
                ))}
              </ul>
              <figcaption className="mt-5 text-sm text-mute">
                The four weakest concepts in a simulated class of 30 made-up students. Bars are drawn at twice their value
                so the differences are easier to see.
              </figcaption>
            </figure>
          </Reveal>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-16 lg:py-24">
          <Reveal>
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Measured, and honest about it</h2>
            <dl className="mt-10 grid gap-8 md:grid-cols-3">
              <div>
                <dt className="text-sm text-mute">Misconceptions identified</dt>
                <dd className="mt-1 text-5xl font-semibold tracking-tighter tabular-nums">18 of 18</dd>
              </div>
              <div>
                <dt className="text-sm text-mute">Error type correct</dt>
                <dd className="mt-1 text-5xl font-semibold tracking-tighter tabular-nums">29 of 30</dd>
              </div>
              <div>
                <dt className="text-sm text-mute">Average time per diagnosis</dt>
                <dd className="mt-1 text-5xl font-semibold tracking-tighter tabular-nums">0.8 s</dd>
              </div>
            </dl>
            <p className="mt-8 max-w-[70ch] text-sm leading-relaxed text-mute">
              Measured on 30 written test cases that weren't used for tuning, running on one PC. They aren't real student
              answers, and no real student has used the tutor yet, so treat this as a check that the system works.
            </p>
          </Reveal>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-16 lg:py-24">
          <Reveal className="flex flex-col items-start justify-between gap-6 rounded-2xl bg-accent-soft p-8 md:flex-row md:items-center md:p-12">
            <h2 className="max-w-[20ch] text-3xl font-semibold tracking-tight md:text-4xl">
              Try it as a student or a teacher
            </h2>
            <PrimaryAction />
          </Reveal>
        </section>
      </main>

      <footer className="mx-auto max-w-7xl border-t border-line px-4 py-8 text-sm text-mute">
        <p>Differential is a hackathon demo of an adaptive exam-prep tutor with a learner model.</p>
      </footer>
    </div>
  )
}
