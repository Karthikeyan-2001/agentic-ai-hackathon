from datetime import datetime, timedelta

import pytest

from engine.scheduling import (
    concept_recall,
    displayed_mastery,
    is_due,
    misconception_recall,
    recall,
    update_stability,
)
from engine.types import ConceptState, MisconceptionState

NOW = datetime(2026, 1, 8)


def test_recall():
    assert recall(0, 2) == 1
    assert recall(2, 2) == pytest.approx(0.3679, abs=0.001)


def test_is_due():
    assert is_due(0.84)
    assert not is_due(0.85)


def test_displayed():
    assert displayed_mastery(0.8, 0.3679) == pytest.approx(0.5472, abs=0.001)


@pytest.mark.parametrize(
    "stability,correct,error_type,expected",
    [
        (2, True, "none", 4),
        (2, True, "slip", 2),
        (2, False, "slip", 2),
        (2, True, "unclear", 2),
        (2, False, "unclear", 2),
        (4, False, "gap", 2),
        (4, True, "misconception", 2),
        (1, False, "gap", 1),
    ],
)
def test_update_stability(stability, correct, error_type, expected):
    assert update_stability(stability, correct, error_type) == expected


def test_concept_recall_never_practised_is_one():
    assert concept_recall(ConceptState("c"), NOW) == 1.0


def test_concept_recall_uses_time_since_practice():
    state = ConceptState("c", stability_days=2, last_practiced_at=NOW - timedelta(days=2))
    assert concept_recall(state, NOW) == pytest.approx(0.3679, abs=0.001)


def test_misconception_recall_is_one_unless_resolved():
    assert misconception_recall(MisconceptionState("m", status="active"), NOW) == 1.0


def test_misconception_recall_measured_from_resolved_at():
    state = MisconceptionState("m", status="resolved", stability_days=3, resolved_at=NOW - timedelta(days=3))
    assert misconception_recall(state, NOW) == pytest.approx(0.3679, abs=0.001)
