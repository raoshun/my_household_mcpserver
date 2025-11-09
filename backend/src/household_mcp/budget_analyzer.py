"""
Budget analysis utilities for legacy CSV data.

This module provides the BudgetAnalyzer class for analyzing
MoneyForward CSV exports.
"""

from pathlib import Path
from typing import Any

import pandas as pd

# MoneyForwardのCSV列名マッピング
COLUMNS_MAP = {
    0: "calc_target",
    1: "date",
    2: "description",
    3: "amount",
    4: "institution",
    5: "major_category",
    6: "minor_category",
    7: "memo",
    8: "transfer",
    9: "id",
}


class BudgetAnalyzer:
    """Analyzes budget data from a CSV file."""

    def __init__(self, csv_path: Path, encoding: str = "shift_jis"):
        """Initialize the BudgetAnalyzer with CSV file path and encoding."""
        self.csv_path = csv_path
        self.encoding = encoding
        self.df = pd.DataFrame(columns=list(COLUMNS_MAP.values()))

    def load_data(self) -> None:
        """Load budget data from the CSV file."""
        try:
            self.df = pd.read_csv(self.csv_path, encoding=self.encoding)
            if len(self.df.columns) >= 10:
                self.df.columns = list(COLUMNS_MAP.values())

            self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
            self.df["amount"] = pd.to_numeric(self.df["amount"], errors="coerce")
            self.df["calc_target"] = pd.to_numeric(
                self.df["calc_target"], errors="coerce"
            )
            print(f"データ読み込み完了: {len(self.df)}件のレコード")

        except (
            FileNotFoundError,
            pd.errors.ParserError,
            UnicodeDecodeError,
        ) as e:
            print(f"データ読み込みエラー: {e}")
            self.df = pd.DataFrame(columns=list(COLUMNS_MAP.values()))

    def get_monthly_summary(self, year: int, month: int) -> dict[str, Any]:
        """Return a summary of monthly budget data for specified period."""
        if self.df.empty:
            return {"message": "No data available."}

        mask = (self.df["date"].dt.year == year) & (self.df["date"].dt.month == month)
        monthly_data = self.df[mask]

        if monthly_data.empty:
            return {"message": f"No data for {year}-{month:02d}."}

        income_data = monthly_data[monthly_data["amount"] > 0]
        expense_data = monthly_data[monthly_data["amount"] < 0]

        total_income = income_data["amount"].sum()
        total_expense = abs(expense_data["amount"].sum())
        balance = total_income - total_expense

        category_summary = (
            expense_data.groupby("minor_category")["amount"]
            .sum()
            .abs()
            .sort_values(ascending=False)
        )

        summary = {
            "period": f"{year}-{month:02d}",
            "total_income": int(total_income),
            "total_expense": int(total_expense),
            "balance": int(balance),
            "expense_by_category": category_summary.to_dict(),
            "transaction_count": len(monthly_data),
        }
        return summary
