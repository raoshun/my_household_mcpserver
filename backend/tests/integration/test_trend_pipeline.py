"""E2E pipeline test for trend analysis: query -> analyzer -> formatter."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from household_mcp.analysis import CategoryTrendAnalyzer
from household_mcp.tools.trend_tool import get_category_trend
from household_mcp.utils import resolve_trend_query


def test_end_to_end_pipeline_with_real_data() -> None:
    # 実データ（data/ 以下）を利用したエンドツーエンド確認
    DATA_DIR = "data"
    # CIなど実データが同梱されない環境ではスキップ
    required = [
        Path(DATA_DIR) / "収入・支出詳細_2022-01-01_2022-01-31.csv",
        Path(DATA_DIR) / "収入・支出詳細_2022-02-01_2022-02-28.csv",
    ]
    if any(not p.exists() for p in required):
        pytest.skip("実データCSVが見つからないため統合テストをスキップします")
    available = [
        {"year": 2022, "month": 1},
        {"year": 2022, "month": 2},
    ]
    categories = ["食費", "交通", "住居", "水道・光熱", "通信"]

    query = resolve_trend_query(
        category="食費",
        start_month="2022-01",
        end_month="2022-02",
        available_months=available,
        available_categories=categories,
    )

    analyzer = CategoryTrendAnalyzer(src_dir=DATA_DIR)
    metrics = analyzer.metrics_for_query(query)
    assert metrics, "metrics should not be empty"
    assert metrics[-1].category == "食費"
    assert metrics[0].month == date(2022, 1, 1)
    assert metrics[-1].month == date(2022, 2, 1)

    resp = get_category_trend(
        category="食費", start_month="2022-01", end_month="2022-02", src_dir=DATA_DIR
    )
    assert resp["category"] == "食費"
    assert resp["metrics"] and len(resp["metrics"]) == 2
    assert "食費の 2022年01月〜2022年02月" in resp["text"]


def test_pipeline_with_missing_category() -> None:
    """Test pipeline with a category that doesn't exist in the data."""
    DATA_DIR = "data"
    required = Path(DATA_DIR) / "収入・支出詳細_2022-01-01_2022-01-31.csv"
    if not required.exists():
        pytest.skip("実データCSVが見つからないため統合テストをスキップします")

    # Use a non-existent category - should raise ValidationError
    from household_mcp.exceptions import ValidationError

    with pytest.raises(ValidationError, match="利用可能なリストに存在しません"):
        get_category_trend(
            category="存在しないカテゴリXYZ123",
            start_month="2022-01",
            end_month="2022-01",
            src_dir=DATA_DIR,
        )


def test_pipeline_with_no_category_specified() -> None:
    """Test pipeline when no category is specified (None means all categories)."""
    DATA_DIR = "data"
    required = Path(DATA_DIR) / "収入・支出詳細_2022-01-01_2022-01-31.csv"
    if not required.exists():
        pytest.skip("実データCSVが見つからないため統合テストをスキップします")

    # Call with None for category (means analyze all categories)
    resp = get_category_trend(
        category=None, start_month="2022-01", end_month="2022-01", src_dir=DATA_DIR
    )

    # When no category specified, response format is different (has "details" instead)
    assert "details" in resp
    assert resp["details"] is not None
    # Should return summary for multiple top categories
    assert len(resp["details"]) > 0
    # Each detail should have category, text, metrics
    for detail in resp["details"]:
        assert "category" in detail
        assert "text" in detail
        assert "metrics" in detail


def test_pipeline_with_invalid_date_range() -> None:
    """Test pipeline with end date before start date."""
    DATA_DIR = "data"
    required = Path(DATA_DIR) / "収入・支出詳細_2022-01-01_2022-01-31.csv"
    if not required.exists():
        pytest.skip("実データCSVが見つからないため統合テストをスキップします")

    # Try to use end date before start date
    from household_mcp.exceptions import ValidationError

    with pytest.raises(
        ValidationError, match="開始月は終了月より前である必要があります"
    ):
        get_category_trend(
            category="食費",
            start_month="2022-02",
            end_month="2022-01",  # Before start
            src_dir=DATA_DIR,
        )


def test_pipeline_single_month() -> None:
    """Test pipeline with a single month (start == end)."""
    DATA_DIR = "data"
    required = Path(DATA_DIR) / "収入・支出詳細_2022-01-01_2022-01-31.csv"
    if not required.exists():
        pytest.skip("実データCSVが見つからないため統合テストをスキップします")

    resp = get_category_trend(
        category="食費", start_month="2022-01", end_month="2022-01", src_dir=DATA_DIR
    )

    assert resp["category"] == "食費"
    assert len(resp["metrics"]) == 1
    assert resp["metrics"][0]["month"] == "2022-01"


def test_pipeline_cache_behavior() -> None:
    """Test that repeated calls use cache effectively."""
    DATA_DIR = "data"
    required = Path(DATA_DIR) / "収入・支出詳細_2022-01-01_2022-01-31.csv"
    if not required.exists():
        pytest.skip("実データCSVが見つからないため統合テストをスキップします")

    # First call - should populate cache
    resp1 = get_category_trend(
        category="食費", start_month="2022-01", end_month="2022-01", src_dir=DATA_DIR
    )

    # Second call with same parameters - should use cache
    resp2 = get_category_trend(
        category="食費", start_month="2022-01", end_month="2022-01", src_dir=DATA_DIR
    )

    # Results should be identical
    assert resp1 == resp2


def test_pipeline_multiple_months_aggregation() -> None:
    """Test pipeline correctly aggregates data across multiple months."""
    DATA_DIR = "data"
    required = [
        Path(DATA_DIR) / "収入・支出詳細_2022-01-01_2022-01-31.csv",
        Path(DATA_DIR) / "収入・支出詳細_2022-02-01_2022-02-28.csv",
    ]
    if any(not p.exists() for p in required):
        pytest.skip("実データCSVが見つからないため統合テストをスキップします")

    resp = get_category_trend(
        category="食費", start_month="2022-01", end_month="2022-02", src_dir=DATA_DIR
    )

    assert len(resp["metrics"]) == 2
    # Check that months are in chronological order
    months = [m["month"] for m in resp["metrics"]]
    assert months == sorted(months)

    # Check that each metric has required fields
    for metric in resp["metrics"]:
        assert "month" in metric
        assert "amount" in metric
        assert isinstance(metric["amount"], (int, float))


def test_pipeline_year_over_year_calculation() -> None:
    """Test that year-over-year metrics are calculated when data is available."""
    DATA_DIR = "data"
    # Need data from same month in consecutive years
    required = [
        Path(DATA_DIR) / "収入・支出詳細_2023-01-01_2023-01-31.csv",
        Path(DATA_DIR) / "収入・支出詳細_2024-01-01_2024-01-31.csv",
    ]
    if any(not p.exists() for p in required):
        pytest.skip("実データCSVが見つからないため統合テストをスキップします")

    # Query for 2024-01, which should have YoY comparison with 2023-01
    resp = get_category_trend(
        category="食費", start_month="2024-01", end_month="2024-01", src_dir=DATA_DIR
    )

    # Check that YoY metric is present
    if resp["metrics"]:
        metric = resp["metrics"][0]
        # year_over_year might be None if not enough history, but field should exist
        assert "year_over_year" in metric or "yoy_change" in metric
