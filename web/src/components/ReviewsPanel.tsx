import { percent } from '../api'
import type { StudentState } from '../types'

export function ReviewsPanel({ state }: { state: StudentState }) {
  const beliefs = state.misconceptions.filter((item) => item.status === 'active' || item.status === 'resolved')

  return (
    <section className="rounded-lg border border-line bg-card p-5">
      <h2 className="font-semibold">Reviews due</h2>
      <p className="mt-1 text-xs text-mute">
        {state.offset_days > 0 ? `Your teacher moved the demo clock ${state.offset_days} days ahead.` : 'The demo clock is on today.'}
      </p>

      {state.due_reviews.length === 0 ? (
        <p className="mt-3 text-sm text-mute">Nothing is due yet.</p>
      ) : (
        <ul className="mt-3 space-y-1 text-sm">
          {state.due_reviews.map((review) => (
            <li key={`${review.kind}-${review.id}`} className="flex justify-between gap-3">
              <span>
                {review.kind === 'misconception' ? 'Recheck: ' : ''}
                {review.name}
              </span>
              <span className="whitespace-nowrap text-mute">recall {percent(review.recall)}</span>
            </li>
          ))}
        </ul>
      )}

      {beliefs.length > 0 && (
        <>
          <h3 className="mt-4 text-xs font-semibold tracking-wide text-mute uppercase">Misconceptions</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {beliefs.map((belief) => (
              <li key={belief.id}>
                <span
                  className={`mr-2 rounded-full px-2 py-0.5 text-xs font-semibold ${
                    belief.status === 'active' ? 'bg-bad-soft text-bad' : 'bg-good-soft text-good'
                  }`}
                >
                  {belief.status === 'active' ? 'Active' : 'Cleared'}
                </span>
                {belief.description}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
