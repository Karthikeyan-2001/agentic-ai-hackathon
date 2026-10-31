import { useState } from 'react'
import { ProgramBlock } from '../QuestionStem'

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
    answer: '5 times',
    correct: false,
    reasoning: 'It counts up to and including 5',
    diagnosis: 'Believes range includes its stop value.',
    mastery: '30% to 5%',
    masteryNote: 'A wrong answer built on a false belief lowers mastery.',
    explanations: [
      ['range includes the stop', 72],
      ['The stop is the repeat count', 24],
    ],
    nextQuestion: 'What is the last number printed by a loop over range(3, 7)?',
  },
  {
    id: 'B',
    name: 'Student B',
    answer: '5 times',
    correct: false,
    reasoning: 'The 5 says how many times',
    diagnosis: 'Believes the stop value says how many times the loop runs.',
    mastery: '30% to 5%',
    masteryNote: 'The same wrong answer as Student A, for a different reason.',
    explanations: [
      ['The stop is the repeat count', 68],
      ['range includes the stop', 24],
    ],
    nextQuestion: 'How many times does the body of a loop over range(4, 6) run?',
  },
  {
    id: 'C',
    name: 'Student C',
    answer: '4 times',
    correct: true,
    reasoning: 'It is always one less than the stop number',
    diagnosis: 'Takes one away from the stop value and ignores the start value.',
    mastery: '30% to 30%',
    masteryNote: 'The right answer for the wrong reason earns no credit.',
    explanations: [['Always one less than the stop', 68]],
    nextQuestion: 'How many times does the body of a loop over range(3, 8) run?',
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
          How many times does the body of this loop run?
        </p>
        <div className="max-w-md">
          <ProgramBlock code={'for i in range(1, 5):\n    print(i)'} />
        </div>
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
              <dt className="text-sm text-mute">Mastery of for loops with range</dt>
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
