import { percent } from '../api'
import type { AnswerResponse, ErrorType } from '../types'

const DIAGNOSIS_TITLE: Record<ErrorType, string> = {
  none: 'Your reasoning is sound',
  misconception: 'A misconception showed up',
  slip: 'Your method looks right, with a careless slip',
  gap: 'This looks like a knowledge gap',
  unclear: "The tutor can't tell yet from this answer",
}

interface Props {
  result: AnswerResponse
  onNext: () => void
  loading: boolean
}

export function ResultCard({ result, onNext, loading }: Props) {
  const { diagnosis } = result
  const flawedButCorrect = result.correct && diagnosis.error_type === 'misconception'
  const main = result.mastery_changes[0]

  return (
    <section className="rounded-lg border border-line bg-card p-6" aria-live="polite">
      <p
        className={`inline-block rounded-full px-3 py-1 text-sm font-semibold ${
          result.correct ? 'bg-good-soft text-good' : 'bg-bad-soft text-bad'
        }`}
      >
        {result.correct ? 'Correct answer' : 'Wrong answer'}
      </p>
      <h2 className="mt-3 text-xl font-semibold">{DIAGNOSIS_TITLE[diagnosis.error_type]}</h2>

      {diagnosis.misconception_description && <p className="mt-2 text-base">{diagnosis.misconception_description}</p>}
      {diagnosis.evidence_quote && (
        <blockquote className="mt-3 border-l-4 border-accent pl-3 text-mute">
          You wrote: “{diagnosis.evidence_quote}”
        </blockquote>
      )}
      {flawedButCorrect && (
        <p className="mt-3 rounded-md bg-warn-soft px-3 py-2 text-sm text-warn">
          The answer is right, but the reason isn't, so this doesn't count towards mastery.
        </p>
      )}
      {result.diagnosis_status === 'failed' && (
        <p className="mt-3 rounded-md bg-warn-soft px-3 py-2 text-sm text-warn">
          The reasoning couldn't be read just now, so this update uses your selected answer only.
        </p>
      )}

      {main && (
        <p className="mt-4 text-sm">
          <span className="font-semibold">{main.name}:</span> {percent(main.before)} → {percent(main.after)}
        </p>
      )}

      <button
        type="button"
        onClick={onNext}
        disabled={loading}
        className="mt-5 rounded-md bg-accent px-5 py-2.5 font-semibold text-white disabled:opacity-40"
      >
        {result.caught_up ? 'Finish' : 'Next question'}
      </button>
    </section>
  )
}
