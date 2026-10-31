from dataclasses import dataclass
from typing import Callable


def ohm_current(v: float, r: float) -> float:
    return v / r


def ohm_voltage(i: float, r: float) -> float:
    return i * r


def ohm_resistance(v: float, i: float) -> float:
    return v / i


def series_resistance(*rs: float) -> float:
    return sum(rs)


def parallel_resistance(*rs: float) -> float:
    return 1 / sum(1 / r for r in rs)


def power(v: float, i: float) -> float:
    return v * i


def power_from_voltage_resistance(v: float, r: float) -> float:
    return v * v / r


def power_from_current_resistance(i: float, r: float) -> float:
    return i * i * r


def energy(p: float, t: float) -> float:
    return p * t


SOLVERS: dict[str, Callable[..., float]] = {
    "ohm_current": ohm_current,
    "ohm_voltage": ohm_voltage,
    "ohm_resistance": ohm_resistance,
    "series_resistance": series_resistance,
    "parallel_resistance": parallel_resistance,
    "power": power,
    "power_from_voltage_resistance": power_from_voltage_resistance,
    "power_from_current_resistance": power_from_current_resistance,
    "energy": energy,
}


@dataclass(frozen=True)
class SolverSpec:
    arg_units: tuple[str, ...]  # With variadic=True, the single unit applies to every argument.
    result_unit: str
    stem_words: tuple[str, ...]
    variadic: bool = False


SOLVER_SPECS: dict[str, SolverSpec] = {
    "ohm_current": SolverSpec(("V", "ohm"), "A", ("current",)),
    "ohm_voltage": SolverSpec(("A", "ohm"), "V", ("voltage", "potential difference")),
    "ohm_resistance": SolverSpec(("V", "A"), "ohm", ("resistance",)),
    "series_resistance": SolverSpec(("ohm",), "ohm", ("series",), variadic=True),
    "parallel_resistance": SolverSpec(("ohm",), "ohm", ("parallel",), variadic=True),
    "power": SolverSpec(("V", "A"), "W", ("power",)),
    "power_from_voltage_resistance": SolverSpec(("V", "ohm"), "W", ("power",)),
    "power_from_current_resistance": SolverSpec(("A", "ohm"), "W", ("power",)),
    "energy": SolverSpec(("kW", "hour"), "kWh", ("energy",)),
}

NUMERIC_CONCEPTS: dict[str, list[str]] = {
    "ohms_law": ["ohm_current", "ohm_voltage", "ohm_resistance"],
    "series_resistance": ["series_resistance"],
    "parallel_resistance": ["parallel_resistance"],
    "electric_power": ["power", "power_from_voltage_resistance", "power_from_current_resistance"],
    "electric_energy": ["energy"],
}
