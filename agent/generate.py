import math
import random
import re

from pydantic import BaseModel

from agent.content import Content
from agent.llm import LLMClient, LLMError
from agent.solvers import NUMERIC_CONCEPTS, SOLVER_SPECS, SOLVERS, SolverSpec, program_for
from engine.types import Option, Question

MAX_ATTEMPTS = 3
MAX_ARGUMENT = 50

FRIENDLY_VALUES = {
    "dividend": [13, 17, 19, 23, 26, 29, 38],
    "divisor": [3, 4, 5, 6, 7],
    "base": [2, 3, 4, 5],
    "exponent": [2, 3],
    "start": [1, 2, 3, 4],
    "stop": [5, 6, 7, 8, 10],
    "outer": [2, 3, 4],
    "inner": [2, 3, 4, 5],
    "item": [2, 3, 5, 8, 10, 12, 15, 20],
}

SYSTEM = """You write multiple-choice questions about what a short Python program prints, for Class 10 computer science.

Rules:
- Use the function and argument values you are given, in that order.
- The stem is one short question: "What does this program print?". For nested_count, use "How many stars does this program print?" instead.
- The program is added to the stem for you, so the stem must contain no code and no digits.
- Give 3 or 4 options with different values. One value must equal the function's result.
- Every wrong option should be a value a student could reach by a real mistake.
- A wrong option may name a listed misconception ID when that belief leads to that value. Otherwise use null.
- The correct option must have a null misconception ID.
- difficulty_prior runs from 1 (easiest) to 5 (hardest).

What the functions calculate:
- floor_div(a, b): the result of a // b, which drops the part after the decimal point
- modulo(a, b): the result of a % b, which is the remainder
- power_of(a, b): the result of a ** b
- range_sum(start, stop): the total of the numbers in range(start, stop), which leaves out stop
- nested_count(outer, inner): the number of stars printed by a loop of inner passes inside a loop of outer passes
- list_total(each item): the total of the items in a list"""


class GeneratedOption(BaseModel):
    value: float
    misconception_id: str | None


class GeneratedQuestion(BaseModel):
    stem: str
    function: str
    args: list[float]
    options: list[GeneratedOption]
    difficulty_prior: int


def _whole_args(g: GeneratedQuestion) -> list[int]:
    return [int(arg) for arg in g.args]


def _solve(g: GeneratedQuestion) -> int:
    return SOLVERS[g.function](*_whole_args(g))


def _stem_problem(stem: str, spec: SolverSpec) -> str | None:
    """The program holds the numbers, so the stem can't add any that disagree with it."""
    if re.search(r"\d", stem):
        return "stem must contain no digits"
    if not any(word in stem.casefold() for word in spec.stem_words):
        return f"stem must ask about the program, using the words: {spec.stem_words[0]}"
    return None


def _shuffled(options: list[GeneratedOption], question_id: str) -> list[GeneratedOption]:
    """The model tends to list the right answer first, so code sets a repeatable order for each question."""
    order = list(options)
    random.Random(question_id).shuffle(order)
    return order


def _rounded_quotient(g: GeneratedQuestion) -> int | None:
    if g.function != "floor_div":
        return None
    dividend, divisor = _whole_args(g)
    return math.floor(dividend / divisor + 0.5)


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
    if (spec.variadic and len(g.args) < 2) or (not spec.variadic and len(g.args) != len(spec.arg_kinds)):
        return f"wrong argument count for {g.function}"
    if any(arg <= 0 or arg > MAX_ARGUMENT for arg in g.args):
        return f"argument values must be from 1 to {MAX_ARGUMENT}"
    if not all(arg.is_integer() for arg in g.args):
        return "argument values must be whole numbers"
    if spec.is_range and g.args[0] >= g.args[1]:
        return "the range must start below its stop value"
    answer = _solve(g)
    stem_problem = _stem_problem(g.stem, spec)
    if stem_problem:
        return stem_problem
    values = [option.value for option in g.options]
    if len(set(values)) != len(values):
        return "option values must be different"
    matching = [option for option in g.options if option.value == answer]
    if len(matching) != 1:
        return f"exactly one option must match the correct answer {answer}, found {len(matching)}"
    if matching[0].misconception_id is not None:
        return "the correct option can't name a misconception"
    for option in g.options:
        if option.misconception_id is not None and option.misconception_id not in valid_ids:
            return f"unknown misconception {option.misconception_id}"
        if option.misconception_id == "integer_division_rounds" and option.value != _rounded_quotient(g):
            return f"integer_division_rounds must tag the rounded quotient of a // question, not {option.value:g}"
    return None


def to_question(g: GeneratedQuestion, question_id: str, concept_id: str) -> Question:
    answer = _solve(g)
    options = [
        Option(
            id=chr(ord("a") + index),
            text=f"{round(option.value, 2):g}",
            is_correct=option.value == answer,
            misconception_ids=[option.misconception_id] if option.misconception_id else [],
        )
        for index, option in enumerate(_shuffled(g.options, question_id))
    ]
    return Question(
        id=question_id,
        concept_id=concept_id,
        stem=f"{g.stem}\n\n{program_for(g.function, _whole_args(g))}",
        options=options,
        difficulty_prior=g.difficulty_prior,
        source="generated",
    )


def _assignment(concept_id: str, question_id: str) -> tuple[str, list[int]]:
    """Pick a repeatable function and friendly numbers, so questions vary while the model stays at temperature 0."""
    rng = random.Random(question_id)
    function = rng.choice(NUMERIC_CONCEPTS[concept_id])
    spec = SOLVER_SPECS[function]
    if spec.variadic:
        return function, rng.sample(FRIENDLY_VALUES[spec.arg_kinds[0]], rng.choice([3, 4]))
    return function, [rng.choice(FRIENDLY_VALUES[kind]) for kind in spec.arg_kinds]


def generate_question(concept_id: str, question_id: str, content: Content, llm: LLMClient) -> Question | None:
    if concept_id not in NUMERIC_CONCEPTS:
        return None
    function, arguments = _assignment(concept_id, question_id)
    concept = content.concepts[concept_id]
    related = [m for m in content.misconceptions.values() if m.concept_id == concept_id]
    offered = [m for m in related if m.id != "integer_division_rounds" or function == "floor_div"]
    catalogue = "\n".join(f"- {m.id}: {m.description}" for m in offered) or "- None. Use null for every misconception ID."
    prompt = (
        f"Concept: {concept.name}. {concept.description}\n"
        f"Use function {function} with arguments {arguments}.\n"
        f"The program students will see:\n{program_for(function, arguments)}\n"
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
        # The model kept repeating numbers in the wording, so code writes the stem and the model writes the options.
        generated = generated.model_copy(update={"stem": SOLVER_SPECS[function].stem})
        rejection = verify_generated(generated, concept_id, valid_ids)
        if rejection is None:
            return to_question(generated, question_id, concept_id)
    return None
