"""Unit tests for `HouseholdDataLoader` helpers."""

from pathlib import Path

import pandas as pd
import pytest

from household_mcp.dataloader import HouseholdDataLoader
from household_mcp.exceptions import DataSourceError


def test_make_filename_and_path(tmp_path: Path):
    loader = HouseholdDataLoader(src_dir=tmp_path)
    # ensure it doesn't crash
    fn = loader._make_filename(2024, 2)
    assert "2024-02" in fn
    p = loader.month_csv_path(2024, 2)
    assert p.name.endswith("_2024-02-29.csv") or p.name.endswith("_2024-02-28.csv")


def test_normalize_columns_minimal():
    loader = HouseholdDataLoader(src_dir=Path("data"))
    df = pd.DataFrame(
        {
            "計算対象": [1],
            "金額（円）": [-100],
            "日付": ["2024-01-01"],
            "大項目": ["食費"],
            "中項目": ["外食"],
        }
    )
    out = loader._normalize_columns(df)
    assert "年月" in out.columns
    # 金額列はInt64に変換される
    assert out["金額（円）"].dtype.name.startswith("Int")


def test_normalize_columns_missing_required():
    loader = HouseholdDataLoader(src_dir=Path("data"))
    df = pd.DataFrame({"金額（円）": [-100], "日付": ["2024-01-01"]})
    with pytest.raises(DataSourceError):
        loader._normalize_columns(df)
