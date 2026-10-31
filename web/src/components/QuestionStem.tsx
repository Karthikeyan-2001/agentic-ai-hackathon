// A stem is a question, then optionally a blank line and a short Python program.
export function QuestionStem({ stem }: { stem: string }) {
  const [prompt, ...program] = stem.split('\n\n')
  return (
    <>
      <h2 className="mt-2 text-xl leading-snug font-semibold text-balance">{prompt}</h2>
      {program.length > 0 && <ProgramBlock code={program.join('\n\n')} />}
    </>
  )
}

export function ProgramBlock({ code }: { code: string }) {
  return (
    <pre className="mt-3 overflow-x-auto rounded-lg border border-line bg-paper p-4 font-mono text-sm leading-relaxed text-ink">
      <code>{code}</code>
    </pre>
  )
}
