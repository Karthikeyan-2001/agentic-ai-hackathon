import { useEffect, useState } from 'react'
import { ApiError, api, percent } from '../api'
import type { ClassSummary, LessonPlan } from '../types'

function cellClass(value: number | null): string {
  if (value === null) return 'bg-none text-mute'
  if (value < 0.4) return 'bg-bad-soft text-bad'
  if (value < 0.7) return 'bg-warn-soft text-warn'
  return 'bg-good-soft text-good'
}

function StatTile({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-lg border border-line bg-card p-5">
      <p className="text-sm text-mute">{label}</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-mute">{detail}</p>
    </div>
  )
}

function Overview({ summary }: { summary: ClassSummary }) {
  const { overview } = summary
  return (
    <section aria-label="Class overview" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatTile label="Students" value={String(overview.student_count)} detail="In this simulated class" />
      <StatTile
        label="Average mastery"
        value={overview.average_mastery === null ? '–' : percent(overview.average_mastery)}
        detail="Assessed Electricity concepts only"
      />
      <StatTile
        label="Students with a misconception"
        value={`${overview.students_with_active_misconception} of ${overview.student_count}`}
        detail="At least one still active"
      />
      <StatTile
        label="Reviews due"
        value={String(overview.reviews_due)}
        detail={`Per student and concept, across ${summary.reviews_by_concept.length} concepts`}
      />
    </section>
  )
}

function Bar({ fraction }: { fraction: number }) {
  return (
    <div className="h-2.5 rounded-full bg-none" aria-hidden="true">
      <div className="h-2.5 rounded-full bg-accent" style={{ width: percent(fraction) }} />
    </div>
  )
}

function ConceptGaps({ summary }: { summary: ClassSummary }) {
  const assessed = summary.concept_gaps.filter((gap) => gap.average_mastery !== null)
  const unassessed = summary.concept_gaps.filter((gap) => gap.average_mastery === null)
  return (
    <section className="rounded-lg border border-line bg-card p-5">
      <h2 className="text-lg font-semibold">Biggest class gaps</h2>
      <p className="mt-1 text-xs text-mute">Electricity concepts, weakest first, by average mastery.</p>
      <ul className="mt-4 space-y-3">
        {assessed.map((gap) => {
          const average = gap.average_mastery ?? 0
          return (
            <li
              key={gap.concept_id}
              title={`${gap.name}: ${percent(average)} average, ${gap.below_40_count} of ${gap.assessed_count} below 40%`}
            >
              <div className="flex flex-wrap justify-between gap-x-3 text-sm">
                <span className="font-medium">{gap.name}</span>
                <span className="tabular-nums">
                  <span className="font-semibold">{percent(average)}</span>
                  <span className="text-mute">
                    {' · '}
                    {gap.below_40_count} of {gap.assessed_count} below 40%
                  </span>
                </span>
              </div>
              <div className="mt-1">
                <Bar fraction={average} />
              </div>
            </li>
          )
        })}
      </ul>
      {unassessed.length > 0 && (
        <p className="mt-4 text-xs text-mute">
          Not assessed yet: {unassessed.map((gap) => gap.name).join(', ')}.
        </p>
      )}
    </section>
  )
}

function ReviewsDue({ summary }: { summary: ClassSummary }) {
  const largest = summary.reviews_by_concept[0]?.student_count ?? 1
  return (
    <section className="rounded-lg border border-line bg-card p-5">
      <h2 className="font-semibold">Reviews due</h2>
      <p className="mt-1 text-xs text-mute">Students whose predicted recall has dropped below 85%.</p>
      {summary.reviews_by_concept.length === 0 ? (
        <p className="mt-3 text-sm text-mute">Nothing is due yet.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {summary.reviews_by_concept.map((review) => (
            <li key={review.concept_id} title={`${review.name}: ${review.student_count} students due`}>
              <div className="flex justify-between gap-3 text-sm">
                <span>{review.name}</span>
                <span className="font-semibold tabular-nums">{review.student_count}</span>
              </div>
              <div className="mt-1">
                <Bar fraction={review.student_count / largest} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function Heatmap({ summary }: { summary: ClassSummary }) {
  const { concepts, students } = summary.heatmap
  return (
    <section className="rounded-lg border border-line bg-card p-5">
      <h2 className="font-semibold">Mastery by student and concept</h2>
      <p className="mt-1 text-xs text-mute">
        Weakest students and concepts come first. Red is below 40%, amber below 70%, green above. A dash means not
        assessed.
      </p>
      <div className="mt-3 max-h-[28rem] overflow-auto rounded-md border border-line">
        <table className="w-full border-collapse text-xs">
          <thead className="sticky top-0 z-10 bg-card">
            <tr>
              <th scope="col" className="sticky left-0 z-20 bg-card p-2 text-left">
                Student
              </th>
              {concepts.map((concept) => (
                <th scope="col" key={concept.id} className="min-w-20 p-2 text-left align-bottom font-semibold">
                  {concept.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {students.map((student) => (
              <tr key={student.id} className="border-t border-line">
                <th scope="row" className="sticky left-0 bg-card p-2 text-left font-medium whitespace-nowrap">
                  {student.name}
                </th>
                {concepts.map((concept) => {
                  const value = student.mastery[concept.id]
                  return (
                    <td
                      key={concept.id}
                      title={`${student.name}, ${concept.name}: ${value === null ? 'not assessed' : percent(value)}`}
                      className={`p-2 text-center tabular-nums ${cellClass(value)}`}
                    >
                      {value === null ? '–' : percent(value)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function MisconceptionGroups({ summary }: { summary: ClassSummary }) {
  return (
    <section className="rounded-lg border border-line bg-card p-5">
      <h2 className="font-semibold">Shared misconceptions</h2>
      {summary.groups.length === 0 ? (
        <p className="mt-2 text-sm text-mute">No active misconceptions.</p>
      ) : (
        <ul className="mt-3 space-y-3">
          {summary.groups.map((group) => (
            <li key={group.misconception_id}>
              <div className="flex justify-between gap-3 text-sm">
                <span>{group.description}</span>
                <span className="font-semibold whitespace-nowrap">
                  {group.students.length} of {summary.student_count}
                </span>
              </div>
              <div className="mt-1 h-2 rounded-full bg-none" aria-hidden="true">
                <div
                  className="h-2 rounded-full bg-accent"
                  style={{ width: percent(group.students.length / summary.student_count) }}
                />
              </div>
              <p className="mt-1 text-xs text-mute">{group.students.map((student) => student.name).join(', ')}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function RootCauses({ summary }: { summary: ClassSummary }) {
  return (
    <section className="rounded-lg border border-line bg-card p-5">
      <h2 className="font-semibold">Root causes</h2>
      <p className="mt-1 text-xs text-mute">The earliest weak prerequisite behind each low score.</p>
      {summary.root_causes.length === 0 ? (
        <p className="mt-2 text-sm text-mute">No prerequisite gaps found.</p>
      ) : (
        <ul className="mt-3 space-y-2 text-sm">
          {summary.root_causes.map((cause) => (
            <li key={cause.concept_id}>
              <span className="font-semibold">{cause.name}</span>: {cause.student_count}{' '}
              {cause.student_count === 1 ? 'student' : 'students'}
              <span className="block text-xs text-mute">Holds back {cause.affects.join(', ')}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function CalibrationFlags({ summary }: { summary: ClassSummary }) {
  return (
    <section className="rounded-lg border border-line bg-card p-5">
      <h2 className="font-semibold">Difficulty surprises</h2>
      <p className="mt-1 text-xs text-mute">Questions where class results disagree with the predicted difficulty.</p>
      {summary.calibration_flags.length === 0 ? (
        <p className="mt-2 text-sm text-mute">Nothing stands out yet.</p>
      ) : (
        <ul className="mt-3 space-y-3 text-sm">
          {summary.calibration_flags.map((flag) => (
            <li key={flag.question_id}>
              <span className="font-semibold">
                {flag.direction === 'harder' ? 'Harder than predicted' : 'Easier than predicted'}
              </span>{' '}
              (Elo {Math.round(flag.predicted_elo)} → {Math.round(flag.current_elo)}, {flag.attempts} attempts)
              <span className="block text-xs text-mute">{flag.stem}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function MondayPlan({ hasGroups }: { hasGroups: boolean }) {
  const [plan, setPlan] = useState<LessonPlan | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function draft() {
    setBusy(true)
    setError('')
    try {
      setPlan(await api.classPlan())
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'The plan could not be drafted.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="rounded-lg border border-line bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-semibold">What to teach on Monday</h2>
        <button
          type="button"
          onClick={draft}
          disabled={busy || !hasGroups}
          className="rounded-md bg-accent px-3 py-2 text-sm font-semibold text-white disabled:opacity-40"
        >
          {busy ? 'Drafting…' : plan ? 'Show plan again' : 'Draft a plan'}
        </button>
      </div>
      {error && (
        <p role="alert" className="mt-3 rounded-md bg-bad-soft px-3 py-2 text-sm text-bad">
          {error}
        </p>
      )}
      {plan && (
        <div className="mt-3 text-sm">
          <h3 className="text-base font-semibold">{plan.title}</h3>
          <p className="mt-1 text-xs text-mute">
            For {plan.student_count} students: {plan.misconception_description}
          </p>
          <p className="mt-2 whitespace-pre-line">{plan.board_demo}</p>
          <p className="mt-3 font-semibold">Check question</p>
          <p>{plan.check_question_stem}</p>
          <p className="mt-3 text-xs text-mute">AI draft. Review it before you teach it.</p>
        </div>
      )}
    </section>
  )
}

export function TeacherPage() {
  const [summary, setSummary] = useState<ClassSummary | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .classSummary()
      .then(setSummary)
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Something went wrong.'))
  }, [])

  return (
    <div className="mx-auto max-w-7xl space-y-4 px-4 py-6">
      <p className="rounded-md bg-warn-soft px-4 py-3 text-sm font-semibold text-warn">
        Simulated class: this page shows {summary?.student_count ?? 30} made-up students, to show how the dashboard
        works. It isn't real student data.
      </p>
      {error && (
        <p role="alert" className="rounded-md bg-bad-soft px-4 py-3 text-bad">
          {error}
        </p>
      )}
      {summary && summary.student_count === 0 && (
        <section className="rounded-lg border border-line bg-card p-6">
          <h2 className="text-xl font-semibold">No class data yet</h2>
          <p className="mt-2 text-mute">
            Run <code className="font-mono">python -m scripts.seed_class</code> to create the simulated class.
          </p>
        </section>
      )}
      {summary && summary.student_count > 0 && (
        <>
          <Overview summary={summary} />
          <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
            <ConceptGaps summary={summary} />
            <ReviewsDue summary={summary} />
          </div>
          <div className="grid items-start gap-4 lg:grid-cols-2">
            <MisconceptionGroups summary={summary} />
            <div className="space-y-4">
              <RootCauses summary={summary} />
              <MondayPlan hasGroups={summary.groups.length > 0} />
            </div>
          </div>
          <Heatmap summary={summary} />
          <CalibrationFlags summary={summary} />
        </>
      )}
    </div>
  )
}
