"""Integration tests for trend analysis tools."""

from __future__ import annotations

from household_mcp.tools.trend_tool import (
    category_trend_summary,
    get_category_trend,
)


def test_category_trend_summary_latest_window() -> None:
    summary = category_trend_summary(src_dir="data", window=3, top_n=2)

    assert "months" in summary
    assert summary["months"]
    assert len(summary["top_categories"]) <= 2
    assert summary["metrics"]


def test_get_category_trend_for_specific_category() -> None:
    result = get_category_trend(
        category="食費",
        start_month="2025-06",
        end_month="2025-07",
        src_dir="data",
    )

    assert result["category"] == "食費"
    assert result["metrics"]
    assert result["text"].startswith("食費の 2025年06月")


def test_get_category_trend_without_category() -> None:
    result = get_category_trend(
        category=None,
        start_month="2025-06",
        end_month="2025-07",
        src_dir="data",
        top_n=2,
    )

    assert result["category"] is None
    assert result["details"]
    assert len(result["details"]) <= 2
