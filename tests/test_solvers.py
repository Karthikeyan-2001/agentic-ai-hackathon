import pytest

from agent.solvers import NUMERIC_CONCEPTS, SOLVERS


def test_solvers():
    assert SOLVERS["ohm_current"](12, 4) == 3
    assert SOLVERS["ohm_voltage"](2, 3) == 6
    assert SOLVERS["ohm_resistance"](12, 3) == 4
    assert SOLVERS["series_resistance"](2, 3, 5) == 10
    assert SOLVERS["parallel_resistance"](6, 3) == pytest.approx(2)
    assert SOLVERS["power"](12, 2) == 24
    assert SOLVERS["energy"](100, 60) == 6000


def test_numeric_concepts_only_name_known_solvers():
    assert set(NUMERIC_CONCEPTS) == {"ohms_law", "series_resistance", "parallel_resistance", "electric_power", "electric_energy"}
    for functions in NUMERIC_CONCEPTS.values():
        assert set(functions) <= set(SOLVERS)


def test_power_variants():
    assert SOLVERS["power_from_voltage_resistance"](12, 10) == pytest.approx(14.4)
    assert SOLVERS["power_from_current_resistance"](2, 3) == 12


def test_every_solver_declares_units_and_stem_words():
    from agent.solvers import SOLVER_SPECS

    assert set(SOLVER_SPECS) == set(SOLVERS)
