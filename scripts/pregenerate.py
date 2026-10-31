import json
from pathlib import Path

from agent.content import load_content
from agent.generate import generate_question
from agent.llm import OllamaClient
from agent.solvers import NUMERIC_CONCEPTS

TARGET = 20
MAX_ROUNDS = 8
OUTPUT = Path("content/generated_questions.json")


def main() -> None:
    if OUTPUT.exists():
        OUTPUT.unlink()
    content = load_content(Path("content"))
    llm = OllamaClient()
    questions = []
    rejected = 0
    for round_number in range(1, MAX_ROUNDS + 1):
        for concept_id in NUMERIC_CONCEPTS:
            if len(questions) >= TARGET:
                break
            question_id = f"g_{concept_id}_{round_number}"
            question = generate_question(concept_id, question_id, content, llm)
            if question is None:
                rejected += 1
            else:
                questions.append(question)
                print(f"OK {question_id}: {question.stem}", flush=True)
    OUTPUT.write_text(json.dumps([q.model_dump() for q in questions], indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(questions)} questions; {rejected} generation attempts failed.")


if __name__ == "__main__":
    main()
