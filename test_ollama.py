import sys
from typing import Literal
from ollama import chat
from pydantic import BaseModel

class Diagnosis(BaseModel):
    misconception: Literal["range_includes_stop", "range_stop_is_count", "range_one_less_than_stop", "none"]
    first_wrong_step: str
    evidence_quote: str
    confidence: float

SYSTEM = """You diagnose Class 10 Python programming reasoning. Judge the reasoning, not just the answer.
range_includes_stop: believes range(start, stop) includes the stop value.
range_stop_is_count: believes the stop value says how many times the loop runs.
range_one_less_than_stop: believes a loop always runs one less time than its stop value, ignoring the start value.
none: the reasoning is correct."""

QUESTION = "How many times does the body of this loop run?\n\nfor i in range(1, 5):\n    print(i)"

STUDENTS = [
    ("5 times", "It counts up to and including 5", "range_includes_stop"),
    ("5 times", "The 5 says how many times", "range_stop_is_count"),
    ("4 times", "It is always one less than the stop number", "range_one_less_than_stop"),
    ("4 times", "It starts at 1 and stops before 5, so it runs for 1, 2, 3 and 4", "none"),
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
