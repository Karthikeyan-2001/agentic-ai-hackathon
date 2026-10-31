import random
import re

from pydantic import BaseModel

from agent.content import Content
from agent.llm import LLMClient, LLMError
from agent.solvers import NUMERIC_CONCEPTS, SOLVER_SPECS, SOLVERS, SolverSpec
from engine.types import Option, Question

MAX_ATTEMPTS = 3
TOLERANCE = 0.01

UNIT_PATTERNS = {
    "V": r"(?:V|volts?)",
    "A": r"(?:A|amperes?|amps?)",
    "ohm": r"(?:ohms?|Ω)",
    "kW": r"(?:kW|kilowatts?)",
    "hour": r"(?:h|hrs?|hours?)",
}
FRIENDLY_VALUES = {
    "V": [3, 6, 9, 12, 18, 24],
    "A": [0.5, 1, 1.5, 2, 3, 4],
    "ohm": [2, 3, 4, 5, 6, 8, 10, 12, 15, 20],
    "kW": [0.5, 1, 1.5, 2, 3],
    "hour": [2, 3, 4, 5, 8, 10],
}

SYSTEM = """You write multiple-choice numeric questions for Class 10 physics.

Rules:
- Use the function and argument values you are given, in that order.
- The stem must state every value with its unit, such as "12 V", "4 ohm", "2 A", "1.5 kW" or "3 hours".
- The stem must contain no other digits, and must not state the answer.
- Give 3 or 4 options with different values. One value must equal the function's result.
- Every wrong option should be a value a student could reach by a real mistake.
- A wrong option may name a listed misconception ID when that belief leads to that value. Otherwise use null.
- The correct option must have a null misconception ID.
- difficulty_prior runs from 1 (easiest) to 5 (hardest).

What the functions calculate:
- ohm_current(voltage in V, resistance in ohm): the current
- ohm_voltage(current in A, resistance in ohm): the voltage
- ohm_resistance(voltage in V, current in A): the resistance
- series_resistance(each resistance in ohm): the total resistance in series
- parallel_resistance(each resistance in ohm): the total resistance in parallel
- power(voltage in V, current in A): the power
- power_from_voltage_resistance(voltage in V, resistance in ohm): the power
- power_from_current_resistance(current in A, resistance in ohm): the power
- energy(power in kW, time in hours): the energy in kWh"""


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


def _units_for(spec: SolverSpec, count: int) -> tuple[str, ...]:
    return spec.arg_units * count if spec.variadic else spec.arg_units


def _stem_problem(g: GeneratedQuestion, spec: SolverSpec) -> str | None:
    """Check the stem states the numbers the answer was computed from, each with the right unit."""
    stem = g.stem
    numbers = {float(found) for found in re.findall(r"\d+(?:\.\d+)?", stem)}
    if numbers != {float(arg) for arg in g.args}:
        return f"stem numbers {sorted(numbers)} must match the arguments {g.args}"
    for arg, unit in zip(g.args, _units_for(spec, len(g.args))):
        number = re.escape(f"{arg:g}")
        pattern = rf"(?<![\d.]){number}(?:\.0+)?\s*{UNIT_PATTERNS[unit]}(?![A-Za-z])"
        if not re.search(pattern, stem):
            return f"stem must state {arg:g} {unit}"
    if not any(word in stem.casefold() for word in spec.stem_words):
        return f"stem must ask about {' or '.join(spec.stem_words)}"
    return None


def verify_generated(g: GeneratedQuestion, concept_id: str, valid_ids: set[str]) -> str | None:
    if g.function not in SOLVERS:
        return f"unknown function {g.function}"
    if g.function not in NUMERIC_CONCEPTS.get(concept_id, []):
        return f"function {g.function} is not allowed for {concept_id}"
    if len(g.options) < 2:
        return "needs at least 2 options"
    if not 1 <= g.difficulty_prior <= 5:
        return f"difficulty_prior {g.difficulty_prior} is out of range"
    spec = SOLVER_SPECS[g.function]
    if (spec.variadic and len(g.args) < 2) or (not spec.variadic and len(g.args) != len(spec.arg_units)):
        return f"wrong argument count for {g.function}"
    if any(arg <= 0 for arg in g.args):
        return "argument values must be positive"
    answer = _solve(g)
    stem_problem = _stem_problem(g, spec)
    if stem_problem:
        return stem_problem
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
    unit = SOLVER_SPECS[g.function].result_unit
    options = [
        Option(
            id=chr(ord("a") + index),
            text=f"{option.value:g} {unit}",
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


def _assignment(concept_id: str, question_id: str) -> tuple[str, list[float]]:
    """Pick a repeatable function and friendly numbers, so questions vary while the model stays at temperature 0."""
    rng = random.Random(question_id)
    function = rng.choice(NUMERIC_CONCEPTS[concept_id])
    spec = SOLVER_SPECS[function]
    if spec.variadic:
        return function, rng.sample(FRIENDLY_VALUES[spec.arg_units[0]], rng.choice([2, 3]))
    return function, [rng.choice(FRIENDLY_VALUES[unit]) for unit in spec.arg_units]


def generate_question(concept_id: str, question_id: str, content: Content, llm: LLMClient) -> Question | None:
    if concept_id not in NUMERIC_CONCEPTS:
        return None
    function, arguments = _assignment(concept_id, question_id)
    concept = content.concepts[concept_id]
    related = [m for m in content.misconceptions.values() if m.concept_id == concept_id]
    catalogue = "\n".join(f"- {m.id}: {m.description}" for m in related) or "- none"
    prompt = (
        f"Concept: {concept.name}. {concept.description}\n"
        f"Use function {function} with arguments {arguments}.\n"
        f"Misconceptions you may name:\n{catalogue}\n"
        f"Reference for this question: {question_id}."
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
