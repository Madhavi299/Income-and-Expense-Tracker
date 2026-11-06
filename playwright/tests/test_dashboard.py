from datetime import date, timedelta

import pytest

from frontend.pages.dashboard import _period_bounds


@pytest.mark.parametrize(
    ("period", "expected_start"),
    [
        ("Daily", date(2026, 11, 6)),
        ("Weekly", date(2026, 10, 31)),
        ("Monthly", date(2026, 11, 1)),
    ],
)
def test_period_bounds_include_the_selected_period(period, expected_start):
    today = date(2026, 11, 6)

    assert _period_bounds(period, today) == (expected_start, today)


def test_period_bounds_rejects_unknown_period():
    with pytest.raises(ValueError, match="Unsupported dashboard period"):
        _period_bounds("Yearly", date.today())
