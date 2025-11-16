"""
不動産キャッシュフロー分析モジュール

FR-032-4: 不動産キャッシュフロー分析
- 不動産収入と支出の照合
- ネットキャッシュフロー計算
- ROI計算（物件別）
- NFR-041: 物件数10件まで対応
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

from household_mcp.analysis.income_analyzer import IncomeAnalyzer
from household_mcp.dataloader import HouseholdDataLoader

_MONEY_Q = Decimal("0.01")


@dataclass
class RealEstateCashflow:
    """不動産キャッシュフロー結果"""

    property_id: str | None  # None = 全物件合計
    year: int
    month: int | None  # None = 年間
    income: Decimal  # 不動産収入（正）
    expense: Decimal  # 不動産支出（正）
    net_cashflow: Decimal  # 収入 - 支出
    roi: Decimal | None  # ROI (%), None = 計算不可

    def to_dict(self) -> dict:
        return {
            "property_id": self.property_id,
            "year": self.year,
            "month": self.month,
            "income": float(self.income),
            "expense": float(self.expense),
            "net_cashflow": float(self.net_cashflow),
            "roi": float(self.roi) if self.roi is not None else None,
        }


class RealEstateCashflowAnalyzer:
    """不動産キャッシュフロー分析エンジン"""

    REAL_ESTATE_INCOME_KEYWORDS = ["不動産", "家賃収入", "不動産収入"]
    REAL_ESTATE_EXPENSE_KEYWORDS = ["住宅", "不動産", "管理費", "修繕"]

    def __init__(
        self,
        income_analyzer: IncomeAnalyzer,
        data_loader: HouseholdDataLoader,
    ):
        self.income_analyzer = income_analyzer
        self.data_loader = data_loader
        self.property_db = self._load_property_database()

    # ----------------------- Public API -----------------------
    def calculate_cashflow(
        self,
        start_date: date,
        end_date: date,
        property_id: str | None = None,
    ) -> RealEstateCashflow:
        """
        不動産キャッシュフローを計算

        Args:
            start_date: 開始日
            end_date: 終了日
            property_id: 物件ID（Noneの場合は全物件合計）

        Returns:
            RealEstateCashflow

        """
        # 期間の全データ取得
        all_df = self._load_period_data(start_date, end_date)
        if all_df.empty:
            return self._empty_cashflow(start_date, end_date, property_id)

        # 不動産収入抽出
        income_df = self._extract_real_estate_income(all_df, property_id)
        re_income = (
            Decimal(str(income_df["金額（円）"].sum()))
            if not income_df.empty
            else Decimal("0")
        )

        # 不動産支出抽出
        expense_df = self._extract_real_estate_expense(all_df, property_id)
        re_expense = (
            Decimal(str(expense_df["金額（円）"].abs().sum()))
            if not expense_df.empty
            else Decimal("0")
        )

        net_cf = (re_income - re_expense).quantize(_MONEY_Q, rounding=ROUND_HALF_UP)

        # ROI計算（年間のみ、かつ property_id 指定時）
        roi_val: Decimal | None = None
        is_annual = (end_date - start_date).days >= 365
        if property_id and is_annual:
            roi_val = self._calculate_roi_for_property(property_id, net_cf)

        year = start_date.year
        month = start_date.month if start_date.month == end_date.month else None

        return RealEstateCashflow(
            property_id=property_id,
            year=year,
            month=month,
            income=re_income.quantize(_MONEY_Q),
            expense=re_expense.quantize(_MONEY_Q),
            net_cashflow=net_cf,
            roi=roi_val,
        )

    def calculate_roi(self, property_id: str, year: int) -> Decimal:
        """
        不動産ROIを計算

        計算式: ROI = (年間ネットキャッシュフロー / 初期投資額) × 100

        Args:
            property_id: 物件ID
            year: 対象年

        Returns:
            ROI(%)

        """
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        cf_result = self.calculate_cashflow(start, end, property_id)
        annual_cf = cf_result.net_cashflow

        if property_id not in self.property_db:
            return Decimal("0")

        initial = Decimal(
            str(self.property_db[property_id].get("initial_investment", 0))
        )
        if initial <= 0:
            return Decimal("0")

        roi = (annual_cf / initial * 100).quantize(_MONEY_Q, rounding=ROUND_HALF_UP)
        return roi

    # ----------------------- Helpers -----------------------
    def _load_period_data(self, start_date: date, end_date: date) -> pd.DataFrame:
        """期間内の全月データを読み込み"""
        dfs = []
        current = start_date.replace(day=1)
        end_marker = end_date.replace(day=1)
        while current <= end_marker:
            try:
                df = self.data_loader.load(current.year, current.month)
                dfs.append(df)
            except FileNotFoundError:
                pass
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        if not dfs:
            return pd.DataFrame()

        all_data = pd.concat(dfs, ignore_index=True)
        # 日付範囲でフィルタ
        all_data = all_data[
            (all_data["日付"] >= start_date) & (all_data["日付"] <= end_date)
        ]
        return all_data

    def _extract_real_estate_income(
        self, df: pd.DataFrame, property_id: str | None
    ) -> pd.DataFrame:
        """
        不動産収入レコードを抽出

        条件: 金額 > 0 かつ 計算対象=1 かつ 大項目or中項目に不動産キーワード
        """
        if df.empty:
            return pd.DataFrame()

        income_mask = (df["金額（円）"] > 0) & (df["計算対象"] == 1)
        income_df = df[income_mask].copy()
        if income_df.empty:
            return pd.DataFrame()

        # 不動産キーワードでフィルタ
        def is_real_estate_income(row):
            large = str(row.get("大項目", ""))
            medium = str(row.get("中項目", ""))
            text = large + " " + medium
            return any(kw in text for kw in self.REAL_ESTATE_INCOME_KEYWORDS)

        mask = income_df.apply(is_real_estate_income, axis=1)
        result = income_df[mask]

        # property_id 指定がある場合は摘要などでフィルタ（将来拡張）
        # 現状は全物件合計のみ対応
        return result

    def _extract_real_estate_expense(
        self, df: pd.DataFrame, property_id: str | None
    ) -> pd.DataFrame:
        """
        不動産支出レコードを抽出

        条件: 金額 < 0 かつ 計算対象=1 かつ 大項目or中項目に住宅/不動産キーワード
        """
        if df.empty:
            return pd.DataFrame()

        expense_mask = (df["金額（円）"] < 0) & (df["計算対象"] == 1)
        expense_df = df[expense_mask].copy()
        if expense_df.empty:
            return pd.DataFrame()

        def is_real_estate_expense(row):
            large = str(row.get("大項目", ""))
            medium = str(row.get("中項目", ""))
            text = large + " " + medium
            return any(kw in text for kw in self.REAL_ESTATE_EXPENSE_KEYWORDS)

        mask = expense_df.apply(is_real_estate_expense, axis=1)
        result = expense_df[mask]
        return result

    def _calculate_roi_for_property(
        self, property_id: str, annual_cf: Decimal
    ) -> Decimal | None:
        """物件のROIを計算（内部ヘルパー）"""
        if property_id not in self.property_db:
            return None
        initial = Decimal(
            str(self.property_db[property_id].get("initial_investment", 0))
        )
        if initial <= 0:
            return None
        roi = (annual_cf / initial * 100).quantize(_MONEY_Q, rounding=ROUND_HALF_UP)
        return roi

    def _empty_cashflow(
        self, start_date: date, end_date: date, property_id: str | None
    ) -> RealEstateCashflow:
        zero = Decimal("0").quantize(_MONEY_Q)
        year = start_date.year
        month = start_date.month if start_date.month == end_date.month else None
        return RealEstateCashflow(
            property_id=property_id,
            year=year,
            month=month,
            income=zero,
            expense=zero,
            net_cashflow=zero,
            roi=None,
        )

    def _load_property_database(self) -> dict:
        """
        property_database.json から物件情報を読み込み

        フォーマット:
        {
          "property_001": {
            "name": "マンションA",
            "initial_investment": 30000000,
            "purchase_date": "2020-04-01"
          }
        }
        """
        config_path = Path(__file__).parent.parent / "config" / "property_database.json"
        if not config_path.exists():
            return {}

        try:
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
