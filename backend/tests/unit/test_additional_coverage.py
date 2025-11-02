import math
from datetime import date
from pathlib import Path

import pytest

from household_mcp.analysis.trends import CategoryTrendAnalyzer, TrendMetrics
from household_mcp.dataloader import HouseholdDataLoader
from household_mcp.exceptions import AnalysisError, DataSourceError
from household_mcp.tools import trend_tool
from household_mcp.utils.formatters import (
    format_category_trend_response,
    format_currency,
    format_percentage,
)


def _write_csv(path: Path, rows: list[str]):
    header = "日付,計算対象,金額（円）,大項目,中項目\n"
    content = header + "\n".join(rows) + ("\n" if rows else "")
    path.write_text(content, encoding="cp932")


def test_loader_load_year_only_and_month_variants(tmp_path: Path):
    # Create two months for the same year
    _write_csv(
        tmp_path / "収入・支出詳細_2024-06-01_2024-06-30.csv",
        ["2024-06-15,1,-6000,食費,外食"],
    )
    _write_csv(
        tmp_path / "収入・支出詳細_2024-07-01_2024-07-31.csv",
        ["2024-07-10,1,-7000,食費,自炊"],
    )

    loader = HouseholdDataLoader(tmp_path)
    # year only path
    df_year = loader.load(year=2024)
    assert len(df_year) == 2
    # month path
    df_month = loader.load(year=2024, month=7)
    assert len(df_month) == 1


def test_loader_missing_required_column(tmp_path: Path):
    # Missing 計算対象 column triggers DataSourceError
    path = tmp_path / "収入・支出詳細_2024-08-01_2024-08-31.csv"
    content = "日付,金額（円）,大項目,中項目\n2024-08-01,-1000,食費,外食\n"
    path.write_text(content, encoding="cp932")
    with pytest.raises(DataSourceError):
        HouseholdDataLoader(tmp_path).load(year=2024, month=8)


def test_loader_missing_category_column(tmp_path: Path):
    # Remove 中項目 column
    path = tmp_path / "収入・支出詳細_2024-09-01_2024-09-30.csv"
    content = "日付,計算対象,金額（円）,大項目\n2024-09-01,1,-1200,食費\n"
    path.write_text(content, encoding="cp932")
    with pytest.raises(DataSourceError):
        HouseholdDataLoader(tmp_path).load(year=2024, month=9)


def test_resolve_src_dir_not_found():
    with pytest.raises(DataSourceError):
        HouseholdDataLoader("/non/existent/hopefully_xyz_123")


def test_format_percentage_nan():
    assert format_percentage(math.nan) == "N/A"


def test_format_currency_invalid_value():
    with pytest.raises(ValueError):
        format_currency("abc")  # invalid numeric


def test_format_category_trend_response_without_average():
    metrics = [
        TrendMetrics(
            category="食費",
            month=date(2024, 6, 1),
            amount=-6000,
            month_over_month=None,
            year_over_year=None,
            moving_average=-6000.0,
        )
    ]
    text = format_category_trend_response("食費", metrics, include_average=False)
    assert "12か月平均" not in text


def test_analyzer_category_not_found(tmp_path: Path):
    _write_csv(
        tmp_path / "収入・支出詳細_2024-06-01_2024-06-30.csv",
        ["2024-06-15,1,-6000,食費,外食"],
    )
    analyzer = CategoryTrendAnalyzer(src_dir=str(tmp_path))
    months = [(2024, 6)]
    with pytest.raises(AnalysisError):
        analyzer.metrics_for_category(months, category="交通費")


def test_trend_tool_top_categories_path(tmp_path: Path):
    # Provide two months, one category
    _write_csv(
        tmp_path / "収入・支出詳細_2024-06-01_2024-06-30.csv",
        ["2024-06-15,1,-6000,食費,外食"],
    )
    _write_csv(
        tmp_path / "収入・支出詳細_2024-07-01_2024-07-31.csv",
        ["2024-07-10,1,-7000,食費,自炊"],
    )
    result = trend_tool.get_category_trend(src_dir=str(tmp_path), category=None)
    assert result["top_categories"]
    assert result["details"]


def test_trend_tool_available_categories_empty_df(tmp_path: Path):
    # Create a month where filtering will drop all rows (計算対象=0)
    _write_csv(
        tmp_path / "収入・支出詳細_2024-06-01_2024-06-30.csv",
        ["2024-06-15,0,-6000,食費,外食"],
    )
    with pytest.raises(DataSourceError):
        trend_tool.get_category_trend(src_dir=str(tmp_path), category=None)


def test_analyzer_expand_months_error(tmp_path: Path):
    # Create minimal data directory for analyzer initialization
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_csv(
        data_dir / "収入・支出詳細_2024-06-01_2024-06-30.csv",
        ["2024-06-15,1,-1000,食費,外食"],
    )

    analyzer = CategoryTrendAnalyzer(loader=HouseholdDataLoader(str(data_dir)))
    with pytest.raises(AnalysisError):
        analyzer._expand_months(date(2024, 7, 1), date(2024, 6, 1))
