from pydantic import BaseModel

from agent.content import Content
from agent.llm import LLMClient, LLMError
from agent.solvers import NUMERIC_CONCEPTS, SOLVERS
from engine.types import Option, Question

MAX_ATTEMPTS = 3
TOLERANCE = 0.01

SYSTEM = """You write multiple-choice numeric questions for Class 10 physics.

Rules:
- Pick one allowed function and give its numeric arguments in order, using positive values.
- Do not state the answer in the stem.
- Give 3 or 4 options with different values. One value must equal the function's result.
- Every wrong option should be a value a student could reach by a real mistake.
- A wrong option may name a listed misconception ID when that belief leads to that value. Otherwise use null.
- The correct option must have a null misconception ID.
- difficulty_prior runs from 1 (easiest) to 5 (hardest).

Allowed functions and their arguments:
- ohm_current(voltage, resistance)
- ohm_voltage(current, resistance)
- ohm_resistance(voltage, current)
- series_resistance(resistance, resistance, ...)
- parallel_resistance(resistance, resistance, ...)
- power(voltage, current)
- energy(power, time)"""


class GeneratedOption(BaseModel):
    value: float
    misconception_id: str | None


class GeneratedQuestion(BaseModel):
    stem: str
    function: str
    args: list[float]
    unit: str
    options: list[GeneratedOption]
    difficulty_prior: int


def _matches(value: float, answer: float) -> bool:
    return abs(value - answer) <= TOLERANCE * abs(answer)


def _solve(g: GeneratedQuestion) -> float:
    return SOLVERS[g.function](*g.args)


def verify_generated(g: GeneratedQuestion, concept_id: str, valid_ids: set[str]) -> str | None:
    if g.function not in SOLVERS:
        return f"unknown function {g.function}"
    if g.function not in NUMERIC_CONCEPTS.get(concept_id, []):
        return f"function {g.function} is not allowed for {concept_id}"
    if len(g.options) < 2:
        return "needs at least 2 options"
    if not 1 <= g.difficulty_prior <= 5:
        return f"difficulty_prior {g.difficulty_prior} is out of range"
    if any(arg <= 0 for arg in g.args):
        return "argument values must be positive"
    try:
        answer = _solve(g)
    except (TypeError, ZeroDivisionError):
        return f"argument values don't work for {g.function}"
    values = [option.value for option in g.options]
    if len(set(values)) != len(values):
        return "option values must be different"
    matching = [option for option in g.options if _matches(option.value, answer)]
    if len(matching) != 1:
        return f"exactly one option must match the correct answer {answer:g}, found {len(matching)}"
    if matching[0].misconception_id is not None:
        return "the correct option can't name a misconception"
    for option in g.options:
        if option.misconception_id is not None and option.misconception_id not in valid_ids:
            return f"unknown misconception {option.misconception_id}"
    return None


def to_question(g: GeneratedQuestion, question_id: str, concept_id: str) -> Question:
    answer = _solve(g)
    options = [
        Option(
            id=chr(ord("a") + index),
            text=f"{option.value:g} {g.unit}",
            is_correct=_matches(option.value, answer),
            misconception_ids=[option.misconception_id] if option.misconception_id else [],
        )
        for index, option in enumerate(g.options)
    ]
    return Question(
        id=question_id,
        concept_id=concept_id,
        stem=g.stem,
        options=options,
        difficulty_prior=g.difficulty_prior,
        source="generated",
    )


def generate_question(concept_id: str, question_id: str, content: Content, llm: LLMClient) -> Question | None:
    functions = NUMERIC_CONCEPTS.get(concept_id)
    if not functions:
        return None
    concept = content.concepts[concept_id]
    related = [m for m in content.misconceptions.values() if m.concept_id == concept_id]
    catalogue = "\n".join(f"- {m.id}: {m.description}" for m in related) or "- none"
    prompt = (
        f"Concept: {concept.name}. {concept.description}\n"
        f"Allowed functions: {', '.join(functions)}\n"
        f"Misconceptions you may name:\n{catalogue}\n"
        f"Reference for this question: {question_id}. Use different numbers from other questions."
    )
    valid_ids = {m.id for m in related}
    rejection = None
    for _ in range(MAX_ATTEMPTS):
        attempt = prompt if rejection is None else f"{prompt}\nYour last attempt was rejected: {rejection}."
        try:
            generated = llm.complete(SYSTEM, attempt, GeneratedQuestion).value
        except LLMError:
            return None
        rejection = verify_generated(generated, concept_id, valid_ids)
        if rejection is None:
            return to_question(generated, question_id, concept_id)
    return None
