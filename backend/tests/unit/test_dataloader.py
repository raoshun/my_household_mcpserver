"""Tests for household_mcp.dataloader."""

from __future__ import annotations

from pathlib import Path

import pytest

from household_mcp.dataloader import (
    DataSourceError,
    iter_available_months,
    load_csv_from_month,
)


def test_load_csv_from_month_filters_data() -> None:
    csv_path = Path("data") / "収入・支出詳細_2025-07-01_2025-07-31.csv"
    if not csv_path.exists():
        pytest.skip("テスト用CSVファイルが見つからないためテストをスキップします")

    df = load_csv_from_month(2025, 7, src_dir="data")

    assert not df.empty
    assert (df["計算対象"] == 1).all()
    assert (df["金額（円）"] < 0).all()
    assert "年月" in df.columns
    assert df["年月"].dt.year.iloc[0] == 2025


def test_iter_available_months_detects_recent_month() -> None:
    csv_path = Path("data") / "収入・支出詳細_2025-07-01_2025-07-31.csv"
    if not csv_path.exists():
        pytest.skip("テスト用CSVファイルが見つからないためテストをスキップします")

    months = list(iter_available_months(src_dir="data"))

    assert (2025, 7) in months
    assert months == sorted(months)


def test_load_csv_from_month_missing_dir() -> None:
    with pytest.raises(DataSourceError):
        load_csv_from_month(2025, 7, src_dir="missing-data")


def test_load_csv_from_month_missing_file() -> None:
    """Test loading CSV for a month that doesn't exist."""
    with pytest.raises(DataSourceError, match="CSV ファイルが見つかりません"):
        load_csv_from_month(1999, 1, src_dir="data")


def test_load_csv_filters_income() -> None:
    """Test that load_csv_from_month filters out income (positive amounts)."""
    csv_path = Path("data") / "収入・支出詳細_2025-07-01_2025-07-31.csv"
    if not csv_path.exists():
        pytest.skip("テスト用CSVファイルが見つからないためテストをスキップします")

    df = load_csv_from_month(2025, 7, src_dir="data")

    # All amounts should be negative (expenses only)
    assert (df["金額（円）"] < 0).all(), "Income records should be filtered out"


def test_load_csv_filters_non_target() -> None:
    """Test that load_csv_from_month filters out non-target records."""
    csv_path = Path("data") / "収入・支出詳細_2025-07-01_2025-07-31.csv"
    if not csv_path.exists():
        pytest.skip("テスト用CSVファイルが見つからないためテストをスキップします")

    df = load_csv_from_month(2025, 7, src_dir="data")

    # All records should have 計算対象 == 1
    assert (df["計算対象"] == 1).all(), "Non-target records should be filtered out"


def test_load_csv_column_normalization() -> None:
    """Test that column names are normalized correctly."""
    csv_path = Path("data") / "収入・支出詳細_2025-07-01_2025-07-31.csv"
    if not csv_path.exists():
        pytest.skip("テスト用CSVファイルが見つからないためテストをスキップします")

    df = load_csv_from_month(2025, 7, src_dir="data")

    # Check expected normalized columns exist
    expected_columns = ["年月", "金額（円）", "カテゴリ", "内容", "計算対象"]
    for col in expected_columns:
        assert col in df.columns, f"Expected column '{col}' not found"


def test_iter_available_months_empty_dir(tmp_path: Path) -> None:
    """Test iter_available_months with empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    months = list(iter_available_months(src_dir=str(empty_dir)))

    assert months == [], "Empty directory should return no months"


def test_iter_available_months_sorted_order() -> None:
    """Test that iter_available_months returns months in sorted order."""
    csv_path = Path("data")
    if not csv_path.exists():
        pytest.skip("data directory not found")

    months = list(iter_available_months(src_dir="data"))

    # Check that months are sorted
    assert months == sorted(months), "Months should be returned in sorted order"

    # Check that all tuples have valid year/month values
    for year, month in months:
        assert 1 <= month <= 12, f"Invalid month value: {month}"
        assert year >= 2000, f"Invalid year value: {year}"


def test_load_csv_dataframe_structure() -> None:
    """Test that loaded DataFrame has correct structure."""
    csv_path = Path("data") / "収入・支出詳細_2025-07-01_2025-07-31.csv"
    if not csv_path.exists():
        pytest.skip("テスト用CSVファイルが見つからないためテストをスキップします")

    df = load_csv_from_month(2025, 7, src_dir="data")

    # Check DataFrame is not empty
    assert not df.empty, "DataFrame should not be empty"

    # Check that 年月 column has datetime type
    assert df["年月"].dtype.name == "datetime64[ns]", "年月 should be datetime type"

    # Check that all 年月 values match the requested year/month
    assert (df["年月"].dt.year == 2025).all(), "All records should be from year 2025"
    assert (df["年月"].dt.month == 7).all(), "All records should be from month 7"
