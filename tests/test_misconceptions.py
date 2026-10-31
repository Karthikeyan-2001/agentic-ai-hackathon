from datetime import datetime, timedelta

import pytest

from engine.misconceptions import update_misconceptions
from engine.types import Diagnosis, MisconceptionState, Option, Question

NOW = datetime(2026, 1, 1)
WRONG = Option(id="w", text="w", is_correct=False, misconception_ids=["m"])
RIGHT = Option(id="r", text="r", is_correct=True)
QUESTION = Question(id="q", concept_id="c", stem="s", options=[RIGHT, WRONG], difficulty_prior=2, source="seed")
PLAIN = Question(
    id="p",
    concept_id="c",
    stem="s",
    options=[RIGHT, Option(id="w", text="w", is_correct=False)],
    difficulty_prior=2,
    source="seed",
)


def named(misconception_id="m", confidence=0.9):
    return Diagnosis(error_type="misconception", misconception_id=misconception_id, confidence=confidence)


def sound():
    return Diagnosis(error_type="none", confidence=0.9)


def states(**overrides):
    return {"m": MisconceptionState("m", **overrides)}


def test_named_sure_activates():
    result = update_misconceptions(states(), named(), QUESTION, WRONG, False, "sure", NOW)["m"]
    assert result.probability == pytest.approx(0.6485)
    assert result.status == "active" and result.was_active


def test_named_not_sure_is_candidate():
    result = update_misconceptions(states(), named(), QUESTION, WRONG, False, "not_sure", NOW)["m"]
    assert result.probability == pytest.approx(0.4091)
    assert result.status == "candidate" and not result.was_active


def test_option_only_sure():
    diagnosis = Diagnosis(error_type="gap", confidence=0.9)
    result = update_misconceptions(states(), diagnosis, QUESTION, WRONG, False, "sure", NOW)["m"]
    assert result.probability == pytest.approx(0.24)
    assert result.status == "candidate"


def test_option_only_not_sure():
    diagnosis = Diagnosis(error_type="unclear", confidence=0.0)
    result = update_misconceptions(states(), diagnosis, QUESTION, WRONG, False, "not_sure", NOW)["m"]
    assert result.probability == pytest.approx(0.164)
    assert result.status == "inactive"


def test_named_on_correct_answer_counts():
    result = update_misconceptions(states(), named(), PLAIN, RIGHT, True, "sure", NOW)["m"]
    assert result.probability == pytest.approx(0.6485)


def test_two_sound_answers_resolve_from_active():
    current = states(probability=0.6485, status="active", was_active=True)
    current = update_misconceptions(current, sound(), QUESTION, RIGHT, True, "sure", NOW)
    assert current["m"].probability == pytest.approx(0.32425)
    assert current["m"].status == "candidate"
    current = update_misconceptions(current, sound(), QUESTION, RIGHT, True, "sure", NOW)
    assert current["m"].probability == pytest.approx(0.162125)
    assert current["m"].status == "resolved" and current["m"].resolved_at == NOW


def test_sound_answer_without_option_for_m_leaves_it_alone():
    current = states(probability=0.6485, status="active", was_active=True)
    result = update_misconceptions(current, sound(), PLAIN, RIGHT, True, "sure", NOW)["m"]
    assert result.probability == 0.6485


def test_sound_recheck_doubles_stability_and_restarts_clock():
    earlier = NOW - timedelta(days=7)
    current = states(probability=0.16, status="resolved", was_active=True, resolved_at=earlier)
    result = update_misconceptions(current, sound(), QUESTION, RIGHT, True, "sure", NOW)["m"]
    assert result.stability_days == 6
    assert result.resolved_at == NOW
    assert result.status == "resolved"


def test_resolved_returns_to_active():
    current = states(probability=0.16, status="resolved", was_active=True, resolved_at=NOW)
    result = update_misconceptions(current, named(), QUESTION, WRONG, False, "sure", NOW)["m"]
    assert result.probability == pytest.approx(0.6892)
    assert result.status == "active"


def test_input_is_not_mutated():
    current = states()
    update_misconceptions(current, named(), QUESTION, WRONG, False, "sure", NOW)
    assert current["m"].probability == 0.05


def test_missing_state_starts_at_default():
    result = update_misconceptions({}, named(), QUESTION, WRONG, False, "sure", NOW)["m"]
    assert result.probability == pytest.approx(0.6485)
