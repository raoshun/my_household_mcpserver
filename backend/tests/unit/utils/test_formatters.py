"""Tests for formatter utilities."""

from __future__ import annotations

from datetime import date

import pytest

from household_mcp.analysis.trends import TrendMetrics
from household_mcp.utils import (
    format_category_trend_response,
    format_currency,
    format_percentage,
    trend_metrics_to_dict,
)


def test_format_currency_and_percentage() -> None:
    assert format_currency(12345) == "12,345円"
    assert format_currency(None) == "N/A"
    assert format_percentage(0.123) == "12.3%"
    assert format_percentage(None) == "N/A"


def test_format_category_trend_response_and_dict() -> None:
    metrics = [
        TrendMetrics(
            category="食費",
            month=date(2025, 6, 1),
            amount=-6000,
            month_over_month=None,
            year_over_year=None,
            moving_average=-6000.0,
        ),
        TrendMetrics(
            category="食費",
            month=date(2025, 7, 1),
            amount=-5000,
            month_over_month=-1 / 6,
            year_over_year=None,
            moving_average=-5500.0,
        ),
    ]

    text = format_category_trend_response("食費", metrics)
    assert "食費の 2025年06月〜2025年07月" in text
    assert "6,000円" in text
    assert "12か月平均 5,500円" in text

    rows = trend_metrics_to_dict(metrics)
    assert rows[0]["month"] == "2025-06"
    assert rows[1]["month_over_month"] == pytest.approx(-1 / 6)
