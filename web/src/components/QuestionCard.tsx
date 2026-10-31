import { useState } from 'react'
import type { PublicQuestion } from '../types'
import { QuestionStem } from './QuestionStem'

export interface AnswerDraft {
  option_id: string
  reasoning: string
  confidence_tap: 'sure' | 'not_sure'
}

interface Props {
  question: PublicQuestion
  submitting: boolean
  prefill?: AnswerDraft | null
  progress?: string
  onSubmit: (draft: AnswerDraft) => void
}

export function QuestionCard({ question, submitting, prefill, progress, onSubmit }: Props) {
  const [optionId, setOptionId] = useState(prefill?.option_id ?? '')
  const [reasoning, setReasoning] = useState(prefill?.reasoning ?? '')
  const [tap, setTap] = useState<'sure' | 'not_sure' | ''>(prefill?.confidence_tap ?? '')

  const ready = optionId !== '' && reasoning.trim() !== '' && tap !== '' && !submitting

  return (
    <form
      className="rounded-lg border border-line bg-card p-6"
      onSubmit={(event) => {
        event.preventDefault()
        if (ready) onSubmit({ option_id: optionId, reasoning, confidence_tap: tap })
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold tracking-wide text-accent uppercase">{question.concept_name}</p>
        {progress && <p className="text-xs font-semibold text-mute tabular-nums">{progress}</p>}
      </div>
      {question.source === 'generated' && (
        <p className="mt-2 inline-block rounded-full bg-accent-soft px-3 py-1 text-xs font-semibold">
          Generated question, answer checked by code
        </p>
      )}
      <QuestionStem stem={question.stem} />

      <fieldset className="mt-5 space-y-2">
        <legend className="sr-only">Choose your answer</legend>
        {question.options.map((option) => (
          <label
            key={option.id}
            className={`flex cursor-pointer items-center gap-3 rounded-md border px-4 py-3 ${
              optionId === option.id ? 'border-accent bg-accent-soft' : 'border-line hover:border-mute'
            }`}
          >
            <input
              type="radio"
              name="option"
              value={option.id}
              checked={optionId === option.id}
              onChange={() => setOptionId(option.id)}
              className="accent-accent"
            />
            {option.text}
          </label>
        ))}
      </fieldset>

      <label className="mt-5 block text-sm font-semibold" htmlFor="reasoning">
        How did you work it out?
      </label>
      <textarea
        id="reasoning"
        value={reasoning}
        maxLength={2000}
        rows={3}
        onChange={(event) => setReasoning(event.target.value)}
        placeholder="Explain your thinking in your own words"
        className="mt-2 w-full rounded-md border border-line p-3 text-base"
      />
      {prefill && <p className="mt-1 text-xs text-mute">Filled in for the guided demo. You can change it before you submit.</p>}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div role="group" aria-label="How sure are you?" className="flex items-center gap-2">
          <span className="text-sm font-semibold">How sure are you?</span>
          {(
            [
              ['sure', 'Sure'],
              ['not_sure', 'Not sure'],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              aria-pressed={tap === value}
              onClick={() => setTap(value)}
              className={`rounded-full border px-4 py-1.5 text-sm ${
                tap === value ? 'border-accent bg-accent text-on-accent' : 'border-line bg-card hover:border-mute'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          type="submit"
          disabled={!ready}
          className="rounded-md bg-accent px-5 py-2.5 font-semibold text-on-accent disabled:cursor-not-allowed disabled:opacity-40"
        >
          {submitting ? 'Reading your reasoning…' : 'Submit answer'}
        </button>
      </div>
    </form>
  )
}
