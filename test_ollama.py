import sys
from typing import Literal
from ollama import chat
from pydantic import BaseModel

class Diagnosis(BaseModel):
    misconception: Literal["current_consumed", "series_parallel_confusion", "identical_implies_equal", "none"]
    first_wrong_step: str
    evidence_quote: str
    confidence: float

SYSTEM = """You diagnose Class 10 physics reasoning. Judge the reasoning, not just the answer.
current_consumed: believes a component uses up current.
series_parallel_confusion: believes current splits between components in series.
identical_implies_equal: gets equal currents only because the bulbs are identical, not because they are in series.
none: the reasoning is correct."""

QUESTION = "Two bulbs are in series. The current through the first is 0.5 A. What is the current through the second?"

STUDENTS = [
    ("0.25 A", "The first bulb used up half", "current_consumed"),
    ("0.25 A", "The current splits between them", "series_parallel_confusion"),
    ("0.5 A", "The bulbs are identical", "identical_implies_equal"),
    ("0.5 A", "A series circuit has one path, so the current is the same everywhere", "none"),
]

for answer, reasoning, expected in STUDENTS:
    response = chat(
        model=sys.argv[1],
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Question: {QUESTION}\nAnswer: {answer}\nReasoning: {reasoning}"},
        ],
        format=Diagnosis.model_json_schema(),
        options={"temperature": 0, "num_ctx": 8192},
        keep_alive=-1,
    )
    result = Diagnosis.model_validate_json(response.message.content)
    print("PASS" if result.misconception == expected else "FAIL", expected, "->", result.misconception)