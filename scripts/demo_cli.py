import time
from datetime import datetime
from pathlib import Path

from agent.content import load_content
from agent.llm import OllamaClient
from agent.loop import new_snapshot, process_answer

DEMO_QUESTION = "q_series_two_bulbs"
STUDENTS = [
    ("A", "0.25 A", "The first bulb used up half"),
    ("B", "0.25 A", "The current splits between them"),
    ("C", "0.5 A", "The bulbs are identical"),
]


def main() -> None:
    content = load_content(Path("content"))
    llm = OllamaClient()
    question = content.questions[DEMO_QUESTION]
    now = datetime(2026, 1, 1)
    print(question.stem)
    for name, option_text, reasoning in STUDENTS:
        option = next(o for o in question.options if o.text == option_text)
        snapshot = new_snapshot(content, pinned_question_id=DEMO_QUESTION, diagnostic_complete=True)
        started = time.perf_counter()
        outcome = process_answer(snapshot, question, option.id, reasoning, "sure", now, content, llm)
        elapsed = time.perf_counter() - started
        before = next(c for c in outcome.applied.mastery_changes if c["id"] == question.concept_id)
        diagnosis = outcome.diagnosis_result.diagnosis
        print(f"\nStudent {name}: {option_text} because \"{reasoning}\"")
        print(f"  Correct: {outcome.applied.correct}")
        print(f"  Diagnosis: {diagnosis.error_type} / {diagnosis.misconception_id} ({diagnosis.confidence:.2f})")
        print(f"  Quote: {diagnosis.evidence_quote}")
        print(f"  Mastery: {before['before']:.3f} -> {before['after']:.3f}")
        print(f"  Next question: {outcome.next_question.id if outcome.next_question else None}")
        print(f"  Time: {elapsed:.1f} seconds")


if __name__ == "__main__":
    main()
