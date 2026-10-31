import pytest

from engine.elo import expected, is_flagged, starting_elo, update_elo


def test_expected():
    assert expected(1500, 1500) == 0.5


def test_update():
    assert update_elo(1500, 1500, True) == pytest.approx((1516, 1484))
    assert update_elo(1500, 1500, False) == pytest.approx((1484, 1516))


@pytest.mark.parametrize("prior,elo", [(1, 1200), (2, 1350), (3, 1500), (4, 1650), (5, 1800)])
def test_starting(prior, elo):
    assert starting_elo(prior) == elo


def test_flag():
    assert is_flagged(1500, 2, 10)
    assert is_flagged(1200, 2, 10)
    assert not is_flagged(1499, 2, 10)
    assert not is_flagged(1500, 2, 9)
