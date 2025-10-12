"""Negative/edge case tests for resolve_trend_query and helpers."""

from __future__ import annotations

from datetime import date

import pytest

from household_mcp.utils.query_parser import (
    ValidationError,
    resolve_trend_query,
    sorted_available_months,
)

AVAILABLE_MONTHS = [
    {"year": 2025, "month": 5},
    {"year": 2025, "month": 6},
    {"year": 2025, "month": 7},
]


def test_sorted_available_months_invalid_entry() -> None:
    with pytest.raises(ValidationError):
        sorted_available_months([{"year": 2025}])  # missing month


def test_resolve_trend_query_unknown_category() -> None:
    with pytest.raises(ValidationError):
        resolve_trend_query(
            category="存在しない",
            start_month="2025-05",
            end_month="2025-07",
            available_months=AVAILABLE_MONTHS,
            available_categories=["食費", "交通"],
        )


def test_resolve_trend_query_invalid_month_format() -> None:
    with pytest.raises(ValidationError):
        resolve_trend_query(
            category=None,
            start_month="2025/13",  # invalid month
            end_month="2025-07",
            available_months=AVAILABLE_MONTHS,
        )


def test_resolve_trend_query_start_after_end() -> None:
    with pytest.raises(ValidationError):
        resolve_trend_query(
            category=None,
            start_month="2025-07",
            end_month="2025-05",
            available_months=AVAILABLE_MONTHS,
        )


def test_resolve_trend_query_default_window_clamps() -> None:
    # Omit start_month, window=2 (should pick last 2 months)
    query = resolve_trend_query(
        category=None,
        start_month=None,
        end_month="2025-07",
        available_months=AVAILABLE_MONTHS,
        default_window=2,
    )
    assert query.start == date(2025, 6, 1)
    assert query.end == date(2025, 7, 1)
