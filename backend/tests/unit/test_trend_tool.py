"""Tests for `tools/trend_tool` helper functions."""

from datetime import date

import pandas as pd
import pytest

from household_mcp.exceptions import DataSourceError
from household_mcp.tools import trend_tool


def test_month_pairs_same_month():
    s = date(2023, 6, 1)
    e = date(2023, 6, 30)
    pairs = trend_tool._month_pairs(s, e)
    assert pairs == ((2023, 6),)


def test_month_pairs_cross_year():
    s = date(2023, 11, 1)
    e = date(2024, 2, 1)
    pairs = trend_tool._month_pairs(s, e)
    assert pairs == ((2023, 11), (2023, 12), (2024, 1), (2024, 2))


def test_list_available_months_no_months(monkeypatch):
    monkeypatch.setattr(trend_tool, "iter_available_months", lambda src_dir: [])
    with pytest.raises(DataSourceError):
        trend_tool._list_available_months("data")


def test_available_categories(monkeypatch):
    # Simulate month list and a df
    monkeypatch.setattr(
        trend_tool, "_list_available_months", lambda src_dir: [(2024, 1)]
    )

    df = pd.DataFrame({"大項目": ["食費", "光熱費"]})
    monkeypatch.setattr(
        trend_tool, "load_csv_from_month", lambda y, m, src_dir=None: df
    )

    cats = trend_tool._available_categories("data")
    assert isinstance(cats, list)
    assert "食費" in cats
