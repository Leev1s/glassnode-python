from datetime import datetime, timezone

import pytest

from glassnode_python.utils import compute_time_range, period_to_seconds


def test_period_to_seconds_supports_days_months_years():
    assert period_to_seconds("1d") == 24 * 3600
    assert period_to_seconds("3mo") == 3 * 30 * 24 * 3600
    assert period_to_seconds("2y") == 2 * 365 * 24 * 3600


def test_period_to_seconds_rejects_invalid_suffix():
    with pytest.raises(ValueError):
        period_to_seconds("10w")


def test_compute_time_range_uses_period_when_start_missing():
    end = datetime(2024, 1, 10, tzinfo=timezone.utc)
    start_ts, end_ts = compute_time_range(end=end, period="2d")
    assert end_ts - start_ts == 2 * 24 * 3600


def test_compute_time_range_honors_explicit_dates():
    start_ts, end_ts = compute_time_range(
        start="2024-01-01T00:00:00Z",
        end="2024-01-05T00:00:00Z",
    )
    assert end_ts - start_ts == 4 * 24 * 3600
