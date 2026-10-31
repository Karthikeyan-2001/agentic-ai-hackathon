import pytest

from engine.graph import dependents_count, propagate, root_prerequisite_below
from engine.types import Concept


def concept(id, *prerequisites):
    return Concept(id=id, name=id, chapter="E", description="d", prerequisites=list(prerequisites))


CHAIN = {"c": concept("c", "b"), "b": concept("b", "a"), "a": concept("a", "z"), "z": concept("z")}
HALF = {"c": 0.5, "b": 0.5, "a": 0.5, "z": 0.5}


def test_propagate_positive_two_links_only():
    result = propagate(HALF, "c", 0.2, CHAIN)
    assert result["b"] == pytest.approx(0.56)
    assert result["a"] == pytest.approx(0.518)
    assert result["z"] == 0.5
    assert result["c"] == 0.5


def test_propagate_negative_uses_smaller_weight():
    result = propagate(HALF, "c", -0.2, CHAIN)
    assert result["b"] == pytest.approx(0.48)
    assert result["a"] == pytest.approx(0.498)


def test_propagate_does_not_change_input():
    masteries = dict(HALF)
    propagate(masteries, "c", 0.2, CHAIN)
    assert masteries == HALF


def test_propagate_stays_in_range():
    assert propagate({"c": 0.5, "b": 0.99, "a": 0.5, "z": 0.5}, "c", 0.9, CHAIN)["b"] == 0.99
    assert propagate({"c": 0.5, "b": 0.01, "a": 0.5, "z": 0.5}, "c", -0.9, CHAIN)["b"] == 0.01


def test_propagate_uses_shortest_path_once():
    diamond = {
        "d": concept("d", "b", "a"),
        "b": concept("b", "a"),
        "a": concept("a"),
    }
    result = propagate({"d": 0.5, "b": 0.5, "a": 0.5}, "d", 0.2, diamond)
    assert result["a"] == pytest.approx(0.56)


def test_dependents_count_includes_indirect():
    assert dependents_count(CHAIN) == {"c": 0, "b": 1, "a": 2, "z": 3}


def test_root_prerequisite_returns_deepest_below_threshold():
    masteries = {"c": 0.2, "b": 0.3, "a": 0.4, "z": 0.9}
    assert root_prerequisite_below("c", masteries, CHAIN) == "a"


def test_root_prerequisite_none_when_all_above():
    masteries = {"c": 0.2, "b": 0.9, "a": 0.9, "z": 0.9}
    assert root_prerequisite_below("c", masteries, CHAIN) is None
