import { percent } from '../api'
import type { AnswerResponse, NextResponse } from '../types'

const STEP_LABEL = {
  check: 'Check',
  diagnose: 'Diagnose',
  validate: 'Validate',
  update: 'Update',
  decide: 'Decide',
}

interface Props {
  next: NextResponse | null
  result: AnswerResponse | null
}

function Explanations({ hypotheses }: { hypotheses: [string, number][] }) {
  if (hypotheses.length === 0) {
    return <p className="text-sm text-mute">No competing explanations right now.</p>
  }
  return (
    <ul className="space-y-2">
      {hypotheses.map(([id, probability]) => (
        <li key={id}>
          <div className="flex justify-between gap-3 font-mono text-xs">
            <span className="break-all">{id}</span>
            <span>{percent(probability)}</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-none" aria-hidden="true">
            <div className="h-2 rounded-full bg-accent" style={{ width: percent(probability) }} />
          </div>
        </li>
      ))}
    </ul>
  )
}

export function ThinkingPanel({ next, result }: Props) {
  const decide = result?.trace.find((entry) => entry.step === 'decide')
  const hypotheses = (decide?.data.hypotheses as [string, number][] | undefined) ?? next?.hypotheses ?? []
  const reason = result?.next_reason ?? next?.reason

  return (
    <aside className="self-start rounded-lg border border-line bg-card p-5">
      <h2 className="font-semibold">What the agent is thinking</h2>

      <h3 className="mt-4 text-xs font-semibold tracking-wide text-mute uppercase">Current explanations</h3>
      <div className="mt-2">
        <Explanations hypotheses={hypotheses} />
      </div>

      {reason && (
        <>
          <h3 className="mt-4 text-xs font-semibold tracking-wide text-mute uppercase">
            {result ? 'Why the next question' : 'Why this question'}
          </h3>
          <p className="mt-1 text-sm">{reason}</p>
        </>
      )}

      {result && (
        <>
          <h3 className="mt-4 text-xs font-semibold tracking-wide text-mute uppercase">Steps for this answer</h3>
          <ol className="mt-2 space-y-2">
            {result.trace.map((entry) => (
              <li key={entry.step} className="grid grid-cols-[5.5rem_1fr] gap-2 text-sm">
                <span className="font-semibold text-accent">{STEP_LABEL[entry.step]}</span>
                <span>{entry.detail}</span>
              </li>
            ))}
          </ol>
        </>
      )}
    </aside>
  )
}
