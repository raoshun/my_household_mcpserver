"""Tests for CategoryTrendAnalyzer."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from household_mcp.analysis import CategoryTrendAnalyzer
from pathlib import Path
import tempfile
from household_mcp.analysis.trends import TrendMetrics
from household_mcp.utils.query_parser import TrendQuery


@pytest.fixture()
def sample_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "年月": pd.to_datetime(["2025-06-01", "2025-07-01", "2025-06-01", "2025-07-01"]),
            "カテゴリ": ["食費", "食費", "交通", "交通"],
            "金額（円）": [-6000, -5000, -2000, -3000],
        }
    )


class _FakeLoader:
    def __init__(self, df: pd.DataFrame):
        self._df = df
        self._tmpdir = Path(tempfile.mkdtemp(prefix="trend-test-"))

    def load_many(self, months):
        # 実際は months に基づくフィルタも可能だがテストでは完全コピーで十分
        return self._df.copy()

    def month_csv_path(self, year, month):
        # Analyzer のシグネチャ計算用に空ファイルを生成
        end_file = self._tmpdir / f"{year}-{month:02d}.csv"
        if not end_file.exists():
            end_file.touch()
        return end_file

    @property
    def src_dir(self):  # pragma: no cover
        return self._tmpdir


@pytest.fixture()
def analyzer(sample_dataframe: pd.DataFrame) -> CategoryTrendAnalyzer:
    fake = _FakeLoader(sample_dataframe)
    return CategoryTrendAnalyzer(loader=fake)


def test_metrics_for_category(analyzer: CategoryTrendAnalyzer) -> None:
    metrics = analyzer.metrics_for_category(((2025, 6), (2025, 7)), category="食費")

    assert len(metrics) == 2
    latest = metrics[-1]
    assert isinstance(latest, TrendMetrics)
    assert latest.category == "食費"
    assert latest.month == date(2025, 7, 1)
    assert latest.amount == -5000
    assert latest.month_over_month == pytest.approx(-1 / 6, rel=1e-3)
    assert latest.moving_average == pytest.approx(-5500)
    assert latest.year_over_year is None


def test_top_categories(analyzer: CategoryTrendAnalyzer) -> None:
    result = analyzer.top_categories(((2025, 6), (2025, 7)), top_n=2)

    assert result[0] == "食費"
    assert "交通" in result


def test_metrics_for_query(analyzer: CategoryTrendAnalyzer) -> None:
    query = TrendQuery(category="食費", start=date(2025, 6, 1), end=date(2025, 7, 1))
    metrics = analyzer.metrics_for_query(query)

    assert len(metrics) == 2
    assert all(metric.category == "食費" for metric in metrics)
