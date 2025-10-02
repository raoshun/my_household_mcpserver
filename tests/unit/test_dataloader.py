"""Tests for household_mcp.dataloader."""

from __future__ import annotations

import pytest

from household_mcp.dataloader import (
    DataSourceError,
    iter_available_months,
    load_csv_from_month,
)


def test_load_csv_from_month_filters_data() -> None:
    df = load_csv_from_month(2025, 7, src_dir="data")

    assert not df.empty
    assert (df["計算対象"] == 1).all()
    assert (df["金額（円）"] < 0).all()
    assert "年月" in df.columns
    assert df["年月"].dt.year.iloc[0] == 2025


def test_iter_available_months_detects_recent_month() -> None:
    months = list(iter_available_months(src_dir="data"))

    assert (2025, 7) in months
    assert months == sorted(months)


def test_load_csv_from_month_missing_dir() -> None:
    with pytest.raises(DataSourceError):
        load_csv_from_month(2025, 7, src_dir="missing-data")
