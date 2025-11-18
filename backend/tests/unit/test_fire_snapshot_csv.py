"""Unit tests for CSV-based annual expense calculation.

Focus: 12-month direct sum, 6-month annualization, <6-month fallback.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Sequence, Tuple

import pandas as pd

from household_mcp.database.manager import DatabaseManager
from household_mcp.services.fire_snapshot import FireSnapshotService


class FakeLoader:
    def __init__(self, months: Sequence[Tuple[int, int]], monthly_amount: int):
        # months is list of (year, month) tuples available
        self._months = list(months)
        self._monthly_amount = monthly_amount

    def iter_available_months(self) -> Iterable[Tuple[int, int]]:
        return iter(self._months)

    def load_many(self, months: Sequence[Tuple[int, int]]) -> pd.DataFrame:
        # For simplicity produce a dataframe with a single expense per month
        rows = []
        for y, m in months:
            rows.append(
                {
                    "金額（円）": -abs(self._monthly_amount),
                    "年月キー": f"{y}-{m:02d}",
                }
            )
        return pd.DataFrame(rows)


def _create_db(tmp_path) -> DatabaseManager:
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(db_path=str(db_path))
    manager.initialize_database()
    return manager


def test_calculate_annual_from_12_months(tmp_path) -> None:
    db = _create_db(tmp_path)
    months = [(2024, i) for i in range(1, 13)]
    loader = FakeLoader(months, monthly_amount=1000)
    svc = FireSnapshotService(db, data_loader=loader)

    annual = svc._calculate_annual_expense_from_csv(date(2024, 12, 31))
    # 12 months * 1000 = 12_000
    assert annual == 12_000.0


def test_calculate_annual_from_6_months_annualized(tmp_path) -> None:
    db = _create_db(tmp_path)
    months = [(2024, i) for i in range(7, 13)]
    loader = FakeLoader(months, monthly_amount=2000)
    svc = FireSnapshotService(db, data_loader=loader)

    annual = svc._calculate_annual_expense_from_csv(date(2024, 12, 31))
    # 6 months * 2000 * 2 = 24_000
    assert annual == 24_000.0


def test_calculate_annual_insufficient_data_returns_none(tmp_path) -> None:
    db = _create_db(tmp_path)
    months = [(2024, 11), (2024, 12)]  # only 2 months
    loader = FakeLoader(months, monthly_amount=5000)
    svc = FireSnapshotService(db, data_loader=loader)

    annual = svc._calculate_annual_expense_from_csv(date(2024, 12, 31))
    assert annual is None
