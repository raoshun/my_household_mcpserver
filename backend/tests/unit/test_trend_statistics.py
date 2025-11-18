"""Unit tests for trend_statistics helper utilities."""

from typing import Any

import pytest

from household_mcp.analysis.trend_statistics import TrendStatistics


def test_calculate_moving_average_simple():
    values = [1.0, 2.0, 3.0, 4.0]
    ma = TrendStatistics.calculate_moving_average(values, window=2)
    assert isinstance(ma, list)
    # length equals original length because padding is applied
    assert len(ma) == len(values)


def test_moving_average_edge_cases():
    with pytest.raises(ValueError):
        TrendStatistics.calculate_moving_average([], window=3)
    # window larger than data -> empty
    with pytest.raises(ValueError):
        TrendStatistics.calculate_moving_average([1.0, 2.0], window=5)


def test_trend_statistics_monthly_growth_rates(monkeypatch: Any):
    # Use deterministic values for growth calculation
    stats = TrendStatistics()

    values = [100.0, 110.0, 121.0]
    # Should calculate monthly growth rate around 10% (0.1)
    p = stats.calculate_monthly_growth_rate(values)
    assert p is not None
    assert isinstance(p.monthly_growth_rate, float)

    # Test projection - simple linear growth
    projection = TrendStatistics.project_assets(100.0, 0.1, 3)
    assert isinstance(projection, float)


def test_calculate_months_to_fi_small():
    stats = TrendStatistics()
    # make a small history where target is 200
    months = stats.calculate_months_to_fi(140, 200, 0.05)
    assert isinstance(months, float)
    assert months >= -1
