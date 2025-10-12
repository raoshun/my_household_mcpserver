from __future__ import annotations

"""E2E pipeline test for trend analysis: query -> analyzer -> formatter."""

from datetime import date

from household_mcp.analysis import CategoryTrendAnalyzer
from household_mcp.tools.trend_tool import get_category_trend
from household_mcp.utils import resolve_trend_query


def test_end_to_end_pipeline_with_real_data() -> None:
    # 実データ（data/ 以下）を利用したエンドツーエンド確認
    DATA_DIR = "data"
    available = [
        {"year": 2025, "month": 6},
        {"year": 2025, "month": 7},
    ]
    categories = ["食費", "交通", "住居", "水道・光熱", "通信"]

    query = resolve_trend_query(
        category="食費",
        start_month="2025-06",
        end_month="2025-07",
        available_months=available,
        available_categories=categories,
    )

    analyzer = CategoryTrendAnalyzer(src_dir=DATA_DIR)
    metrics = analyzer.metrics_for_query(query)
    assert metrics, "metrics should not be empty"
    assert metrics[-1].category == "食費"
    assert metrics[0].month == date(2025, 6, 1)
    assert metrics[-1].month == date(2025, 7, 1)

    resp = get_category_trend(
        category="食費", start_month="2025-06", end_month="2025-07", src_dir=DATA_DIR
    )
    assert resp["category"] == "食費"
    assert resp["metrics"] and len(resp["metrics"]) == 2
    assert "食費の 2025年06月〜2025年07月" in resp["text"]
