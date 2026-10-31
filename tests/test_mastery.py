import pytest

from engine.mastery import update_mastery


@pytest.mark.parametrize(
    "correct,error_type,expected",
    [
        (True, "none", 0.836),
        (True, "misconception", 0.5),
        (True, "gap", 0.5),
        (True, "slip", 0.643),
        (True, "unclear", 0.643),
        (False, "misconception", 0.111),
        (False, "gap", 0.111),
        (False, "none", 0.111),
        (False, "unclear", 0.111),
        (False, "slip", 0.429),
    ],
)
def test_update_mastery_table(correct, error_type, expected):
    assert update_mastery(0.5, correct, error_type) == pytest.approx(expected, abs=0.001)


def test_mastery_is_clamped():
    assert update_mastery(0.99, True, "none") <= 0.99
    assert update_mastery(0.01, False, "gap") >= 0.01
