import { useState } from 'react'

interface DemoStudent {
  id: string
  name: string
  answer: string
  correct: boolean
  reasoning: string
  diagnosis: string
  mastery: string
  masteryNote: string
  explanations: [string, number][]
  nextQuestion: string
}

// Recorded from the tutor's real demo run on the local model. Nothing on this page calls the model.
const STUDENTS: DemoStudent[] = [
  {
    id: 'A',
    name: 'Student A',
    answer: '0.25 A',
    correct: false,
    reasoning: 'The first bulb used up half',
    diagnosis: 'Believes a component uses up current.',
    mastery: '30% to 5%',
    masteryNote: 'A wrong answer built on a false belief lowers mastery.',
    explanations: [
      ['Current gets used up', 68],
      ['Current splits in series', 24],
    ],
    nextQuestion: 'Ammeters sit just before and just after a glowing bulb. How do their readings compare?',
  },
  {
    id: 'B',
    name: 'Student B',
    answer: '0.25 A',
    correct: false,
    reasoning: 'The current splits between them',
    diagnosis: 'Believes current splits in series, as it does between parallel branches.',
    mastery: '30% to 5%',
    masteryNote: 'The same wrong answer as Student A, for a different reason.',
    explanations: [
      ['Current splits in series', 72],
      ['Current gets used up', 24],
    ],
    nextQuestion: 'Two identical bulbs are wired in series, then in parallel. When does each carry the full battery current?',
  },
  {
    id: 'C',
    name: 'Student C',
    answer: '0.5 A',
    correct: true,
    reasoning: 'The bulbs are identical',
    diagnosis: 'Gets equal currents only because the bulbs are identical, not because they are in series.',
    mastery: '30% to 30%',
    masteryNote: 'The right answer for the wrong reason earns no credit.',
    explanations: [['Identical means equal', 68]],
    nextQuestion: 'A 2 ohm bulb and a 6 ohm bulb are in series, with 0.5 A through the first. What flows through the second?',
  },
]

export function DiagnosisDemo() {
  const [selectedId, setSelectedId] = useState('A')
  const student = STUDENTS.find((item) => item.id === selectedId) ?? STUDENTS[0]

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-card">
      <div className="border-b border-line p-6 md:p-8">
        <p className="text-sm text-mute">The same question for all three students</p>
        <p className="mt-2 max-w-[42ch] text-xl font-medium tracking-tight md:text-2xl">
          Two bulbs are in series. The current through the first is 0.5 A. What is the current through the second?
        </p>
        <div role="tablist" aria-label="Choose a student" className="mt-6 flex flex-wrap gap-2">
          {STUDENTS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              id={`demo-tab-${item.id}`}
              aria-selected={item.id === selectedId}
              aria-controls="demo-panel"
              onClick={() => setSelectedId(item.id)}
              className={`rounded-lg border px-4 py-2 text-sm font-semibold transition active:scale-[0.98] ${
                item.id === selectedId ? 'border-accent bg-accent text-on-accent' : 'border-line hover:border-mute'
              }`}
            >
              {item.name}
            </button>
          ))}
        </div>
      </div>

      <div
        key={student.id}
        id="demo-panel"
        role="tabpanel"
        aria-labelledby={`demo-tab-${student.id}`}
        className="grid md:grid-cols-[2fr_3fr]"
      >
        <div className="border-b border-line p-6 md:border-r md:border-b-0 md:p-8">
          <p className="text-sm text-mute">{student.name} answered</p>
          <p className="mt-1 flex flex-wrap items-baseline gap-3">
            <span className="text-4xl font-semibold tracking-tight tabular-nums">{student.answer}</span>
            <span
              className={`rounded-lg px-2 py-0.5 text-sm font-semibold ${
                student.correct ? 'bg-good-soft text-good' : 'bg-bad-soft text-bad'
              }`}
            >
              {student.correct ? 'Correct' : 'Wrong'}
            </span>
          </p>
          <p className="mt-5 text-sm text-mute">Their reasoning</p>
          <blockquote className="mt-1 border-l-4 border-accent pl-3 text-lg">“{student.reasoning}”</blockquote>
        </div>

        <div className="p-6 md:p-8">
          <p className="text-sm text-mute">Diagnosis</p>
          <p className="mt-1 text-lg font-medium">{student.diagnosis}</p>

          <dl className="mt-6 grid gap-6 sm:grid-cols-2">
            <div>
              <dt className="text-sm text-mute">Mastery of series current</dt>
              <dd className="mt-1 text-2xl font-semibold tabular-nums">{student.mastery}</dd>
              <dd className="mt-1 text-sm text-mute">{student.masteryNote}</dd>
            </div>
            <div>
              <dt className="text-sm text-mute">Explanations still open</dt>
              {student.explanations.map(([name, value]) => (
                <dd key={name} className="mt-2 flex items-center gap-2 text-sm">
                  <span className="h-2 rounded-full bg-accent" style={{ width: `${value * 0.8}px` }} aria-hidden="true" />
                  <span className="font-semibold tabular-nums">{value}%</span>
                  <span>{name}</span>
                </dd>
              ))}
            </div>
          </dl>

          <p className="mt-6 text-sm text-mute">So the tutor asks next</p>
          <p className="mt-1 font-medium">{student.nextQuestion}</p>
        </div>
      </div>
    </div>
  )
}
