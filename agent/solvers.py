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


def energy(p: float, t: float) -> float:
    return p * t


SOLVERS: dict[str, Callable[..., float]] = {
    "ohm_current": ohm_current,
    "ohm_voltage": ohm_voltage,
    "ohm_resistance": ohm_resistance,
    "series_resistance": series_resistance,
    "parallel_resistance": parallel_resistance,
    "power": power,
    "energy": energy,
}

NUMERIC_CONCEPTS: dict[str, list[str]] = {
    "ohms_law": ["ohm_current", "ohm_voltage", "ohm_resistance"],
    "series_resistance": ["series_resistance"],
    "parallel_resistance": ["parallel_resistance"],
    "electric_power": ["power"],
    "electric_energy": ["energy"],
}
