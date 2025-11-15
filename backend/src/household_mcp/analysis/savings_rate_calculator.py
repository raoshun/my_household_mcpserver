"""
貯蓄率計算モジュール

FR-032-3: 貯蓄率計算 / NFR-038 数値精度（%は小数第2位）

- 月次貯蓄率計算
- 期間推移取得
- 固定費 / 変動費分類
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

from household_mcp.analysis.income_analyzer import IncomeAnalyzer, IncomeSummary
from household_mcp.dataloader import HouseholdDataLoader

_PERCENT_Q = Decimal("0.01")


@dataclass
class SavingsMetrics:
    """貯蓄関連メトリクス"""

    year: int
    month: int
    income: Decimal  # 総収入（正）
    expense: Decimal  # 総支出（正）
    savings: Decimal  # 収入 - 支出（負になり得る）
    savings_rate: Decimal  # (savings / income) * 100 (%), income=0は0
    disposable_income: Decimal  # 可処分所得（収入 - 固定費）
    fixed_costs: Decimal  # 固定費合計（正）
    variable_costs: Decimal  # 変動費合計（正）
    variable_cost_ratio: Decimal  # (variable_costs / disposable_income) *100

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "month": self.month,
            "income": float(self.income),
            "expense": float(self.expense),
            "savings": float(self.savings),
            "savings_rate": float(self.savings_rate),
            "disposable_income": float(self.disposable_income),
            "fixed_costs": float(self.fixed_costs),
            "variable_costs": float(self.variable_costs),
            "variable_cost_ratio": float(self.variable_cost_ratio),
        }


class SavingsRateCalculator:
    """貯蓄率計算エンジン"""

    FIXED_COST_KEYWORDS = [
        "住宅",  # 家賃 / ローン
        "水道",  # 水道光熱費
        "光熱",  # 水道光熱費
        "通信",  # 通信費
        "保険",  # 保険
    ]

    def __init__(
        self, income_analyzer: IncomeAnalyzer, data_loader: HouseholdDataLoader
    ):
        self.income_analyzer = income_analyzer
        self.data_loader = data_loader

    # ------------------------- Public API -------------------------
    def calculate_monthly_savings_rate(self, year: int, month: int) -> SavingsMetrics:
        """
        月次貯蓄率を計算

        計算式:
          収入 = IncomeAnalyzer.get_monthly_summary の total_income
          支出 = 金額（円）<0 の絶対値合計（計算対象=1）
          貯蓄額 = 収入 - 支出
          貯蓄率 = (貯蓄額 / 収入) * 100 （収入=0→0）
          固定費 = 固定費キーワードに一致する支出合計
          可処分所得 = 収入 - 固定費
          変動費率 = (変動費 / 可処分所得) * 100
        """
        income_summary: IncomeSummary = self.income_analyzer.get_monthly_summary(
            year, month
        )
        income = income_summary.total_income

        df = self._load_month_df(year, month)
        if df.empty:
            return self._empty_metrics(year, month, income)

        expense_df = df[(df["計算対象"] == 1) & (df["金額（円）"] < 0)].copy()
        if expense_df.empty:
            return self._empty_metrics(year, month, income)

        expense_df["abs_amount"] = expense_df["金額（円）"].abs()

        # 固定費 / 変動費分類
        expense_df["cost_type"] = expense_df.apply(self.classify_cost_type, axis=1)
        fixed_costs_sum = Decimal(
            str(expense_df[expense_df["cost_type"] == "fixed"]["abs_amount"].sum())
        )
        variable_costs_sum = Decimal(
            str(expense_df[expense_df["cost_type"] == "variable"]["abs_amount"].sum())
        )

        total_expense = Decimal(str(expense_df["abs_amount"].sum()))
        savings = (income - total_expense).quantize(_PERCENT_Q)

        if income > 0:
            savings_rate = (savings / income * 100).quantize(
                _PERCENT_Q, rounding=ROUND_HALF_UP
            )
        else:
            savings_rate = Decimal("0")

        disposable_income = (income - fixed_costs_sum).quantize(_PERCENT_Q)
        if disposable_income > 0:
            variable_ratio = (variable_costs_sum / disposable_income * 100).quantize(
                _PERCENT_Q, rounding=ROUND_HALF_UP
            )
        else:
            variable_ratio = Decimal("0")

        return SavingsMetrics(
            year=year,
            month=month,
            income=income.quantize(_PERCENT_Q)
            if isinstance(income, Decimal)
            else Decimal(str(income)).quantize(_PERCENT_Q),
            expense=total_expense.quantize(_PERCENT_Q),
            savings=savings,
            savings_rate=savings_rate,
            disposable_income=disposable_income,
            fixed_costs=fixed_costs_sum.quantize(_PERCENT_Q),
            variable_costs=variable_costs_sum.quantize(_PERCENT_Q),
            variable_cost_ratio=variable_ratio,
        )

    def get_savings_rate_trend(
        self, start_date: date, end_date: date
    ) -> list[SavingsMetrics]:
        """期間の貯蓄率推移を取得（開始月～終了月 inclusive）"""
        metrics: list[SavingsMetrics] = []
        current = start_date.replace(day=1)
        end_marker = end_date.replace(day=1)
        while current <= end_marker:
            metrics.append(
                self.calculate_monthly_savings_rate(current.year, current.month)
            )
            # 次の月
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        return metrics

    # ------------------------- Helpers -------------------------
    def classify_cost_type(self, record: pd.Series) -> str:
        """
        支出を固定費・変動費に分類

        固定費キーワードが『大項目 or 中項目』に含まれていれば fixed、そうでなければ variable。
        """
        large_cat = str(record.get("大項目", ""))
        medium_cat = str(record.get("中項目", ""))
        text = large_cat + " " + medium_cat
        for kw in self.FIXED_COST_KEYWORDS:
            if kw in text:
                return "fixed"
        return "variable"

    def _load_month_df(self, year: int, month: int) -> pd.DataFrame:
        try:
            return self.data_loader.load(year, month)
        except FileNotFoundError:
            return pd.DataFrame()

    def _empty_metrics(self, year: int, month: int, income: Decimal) -> SavingsMetrics:
        income_val = income if isinstance(income, Decimal) else Decimal(str(income))
        zero = Decimal("0").quantize(_PERCENT_Q)
        return SavingsMetrics(
            year=year,
            month=month,
            income=income_val.quantize(_PERCENT_Q),
            expense=zero,
            savings=income_val.quantize(_PERCENT_Q),  # 収入のみの場合、全額貯蓄とみなす
            savings_rate=Decimal("100.00") if income_val > 0 else zero,
            disposable_income=income_val.quantize(_PERCENT_Q),
            fixed_costs=zero,
            variable_costs=zero,
            variable_cost_ratio=zero,
        )
