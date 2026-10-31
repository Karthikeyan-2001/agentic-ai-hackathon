from dataclasses import dataclass
from typing import Callable


def floor_div(a: int, b: int) -> int:
    return a // b


def modulo(a: int, b: int) -> int:
    return a % b


def power_of(base: int, exponent: int) -> int:
    return base**exponent


def range_sum(start: int, stop: int) -> int:
    return sum(range(start, stop))


def nested_count(outer: int, inner: int) -> int:
    return outer * inner


def list_total(*values: int) -> int:
    return sum(values)


SOLVERS: dict[str, Callable[..., int]] = {
    "floor_div": floor_div,
    "modulo": modulo,
    "power_of": power_of,
    "range_sum": range_sum,
    "nested_count": nested_count,
    "list_total": list_total,
}


PRINTED_VALUE_WORDS = ("print", "display", "output", "show", "value", "result")


@dataclass(frozen=True)
class SolverSpec:
    arg_kinds: tuple[str, ...]  # With variadic=True, the single kind applies to every argument.
    program: str
    variadic: bool = False
    is_range: bool = False
    stem_words: tuple[str, ...] = PRINTED_VALUE_WORDS


SOLVER_SPECS: dict[str, SolverSpec] = {
    "floor_div": SolverSpec(("dividend", "divisor"), "print({} // {})"),
    "modulo": SolverSpec(("dividend", "divisor"), "print({} % {})"),
    "power_of": SolverSpec(("base", "exponent"), "print({} ** {})"),
    "range_sum": SolverSpec(
        ("start", "stop"),
        "total = 0\nfor i in range({}, {}):\n    total = total + i\nprint(total)",
        is_range=True,
    ),
    "nested_count": SolverSpec(
        ("outer", "inner"),
        'for i in range({}):\n    for j in range({}):\n        print("*")',
        stem_words=("how many",),
    ),
    "list_total": SolverSpec(
        ("item",),
        "marks = [{}]\ntotal = 0\nfor mark in marks:\n    total = total + mark\nprint(total)",
        variadic=True,
    ),
}

NUMERIC_CONCEPTS: dict[str, list[str]] = {
    "arithmetic_operators": ["floor_div", "modulo", "power_of"],
    "running_total": ["range_sum"],
    "nested_loops": ["nested_count"],
    "list_traversal": ["list_total"],
}


def program_for(function: str, args: list[int]) -> str:
    spec = SOLVER_SPECS[function]
    if spec.variadic:
        return spec.program.format(", ".join(str(arg) for arg in args))
    return spec.program.format(*args)
