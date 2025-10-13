"""Integration tests for trend analysis tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from household_mcp.tools.trend_tool import category_trend_summary, get_category_trend


def test_category_trend_summary_latest_window() -> None:
    # データファイルの存在確認
    data_dir = Path("data")
    if not data_dir.exists() or not any(data_dir.glob("*.csv")):
        pytest.skip("テスト用データファイルが見つからないためテストをスキップします")

    summary = category_trend_summary(src_dir="data", window=3, top_n=2)

    assert "months" in summary
    assert summary["months"]
    assert len(summary["top_categories"]) <= 2
    assert summary["metrics"]


def test_get_category_trend_for_specific_category() -> None:
    # 2025年のデータファイル存在確認
    required_files = [
        Path("data") / "収入・支出詳細_2025-06-01_2025-06-30.csv",
        Path("data") / "収入・支出詳細_2025-07-01_2025-07-31.csv",
    ]
    if any(not f.exists() for f in required_files):
        pytest.skip("テスト用データファイルが見つからないためテストをスキップします")

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
    # 2025年のデータファイル存在確認
    required_files = [
        Path("data") / "収入・支出詳細_2025-06-01_2025-06-30.csv",
        Path("data") / "収入・支出詳細_2025-07-01_2025-07-31.csv",
    ]
    if any(not f.exists() for f in required_files):
        pytest.skip("テスト用データファイルが見つからないためテストをスキップします")

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
