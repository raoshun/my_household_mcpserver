"""
収入分析モジュール

家計簿CSVデータから収入を抽出・分類し、月次/年次サマリーを生成する。
"""

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from household_mcp.dataloader import HouseholdDataLoader


class IncomeCategory:
    """収入カテゴリ定義"""

    SALARY = "給与所得"
    BUSINESS = "事業所得"
    REAL_ESTATE = "不動産所得"
    DIVIDEND = "配当・利子所得"
    OTHER = "その他収入"

    @classmethod
    def all_categories(cls) -> list[str]:
        """すべてのカテゴリを返す"""
        return [cls.SALARY, cls.BUSINESS, cls.REAL_ESTATE, cls.DIVIDEND, cls.OTHER]


@dataclass
class IncomeSummary:
    """収入サマリー"""

    year: int
    month: int | None  # None = 年次サマリー
    total_income: Decimal
    category_breakdown: dict[str, Decimal]  # カテゴリ名 -> 金額
    category_ratios: dict[str, Decimal]  # カテゴリ名 -> 構成比率(%)
    previous_period_change: Decimal | None  # 前月比/前年比(%)
    average_monthly: Decimal | None  # 月平均（年次のみ）

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "year": self.year,
            "month": self.month,
            "total_income": float(self.total_income),
            "category_breakdown": {
                k: float(v) for k, v in self.category_breakdown.items()
            },
            "category_ratios": {k: float(v) for k, v in self.category_ratios.items()},
            "previous_period_change": (
                float(self.previous_period_change)
                if self.previous_period_change is not None
                else None
            ),
            "average_monthly": (
                float(self.average_monthly)
                if self.average_monthly is not None
                else None
            ),
        }


class IncomeAnalyzer:
    """収入分析エンジン"""

    def __init__(self, data_loader: HouseholdDataLoader):
        """
        Initialize IncomeAnalyzer.

        Args:
            data_loader: 家計簿データローダー

        """
        self.data_loader = data_loader
        self.category_rules = self._load_category_rules()

    def extract_income_records(self, start_date: date, end_date: date) -> pd.DataFrame:
        """
        指定期間の収入レコードを抽出

        条件:
        - 金額（円）> 0
        - 計算対象 = 1

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            収入レコードのDataFrame

        """
        # 期間の月をすべて取得
        all_months = []
        current = start_date.replace(day=1)
        end_month = end_date.replace(day=1)

        while current <= end_month:
            all_months.append((current.year, current.month))
            # 次の月へ
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        # 各月のデータを読み込み
        dfs = []
        for year, month in all_months:
            try:
                df = self.data_loader.load(year, month)
                dfs.append(df)
            except FileNotFoundError:
                # データがない月はスキップ
                continue

        if not dfs:
            return pd.DataFrame()

        # すべてのデータを結合
        all_data = pd.concat(dfs, ignore_index=True)

        # 収入レコードを抽出: 金額 > 0 かつ 計算対象 = 1
        income_records = all_data[
            (all_data["金額（円）"] > 0) & (all_data["計算対象"] == 1)
        ].copy()

        # 日付でフィルタリング
        income_records = income_records[
            (income_records["日付"] >= pd.Timestamp(start_date))
            & (income_records["日付"] <= pd.Timestamp(end_date))
        ]

        return income_records

    def classify_income(self, record: pd.Series) -> str:
        """
        収入レコードを5カテゴリに分類

        分類ルール:
        1. 大項目 or 中項目に「給与」「賞与」→ 給与所得
        2. 大項目 or 中項目に「事業」→ 事業所得
        3. 大項目 or 中項目に「不動産」「家賃収入」→ 不動産所得
        4. 大項目 or 中項目に「配当」「利子」「分配金」→ 配当・利子所得
        5. その他 → その他収入

        Args:
            record: 収入レコード（pandas Series）

        Returns:
            IncomeCategory の文字列値

        """
        large_cat = str(record.get("大項目", ""))
        medium_cat = str(record.get("中項目", ""))

        # 各カテゴリのキーワードでマッチング
        for _category_key, rule in self.category_rules.items():
            # 大項目でマッチング
            if any(kw in large_cat for kw in rule.get("large_keywords", [])):
                return rule["category"]

            # 中項目でマッチング
            if any(kw in medium_cat for kw in rule.get("medium_keywords", [])):
                return rule["category"]

        # どれにも該当しない場合はその他収入
        return IncomeCategory.OTHER

    def get_monthly_summary(
        self, year: int, month: int, *, include_previous_change: bool = True
    ) -> IncomeSummary:
        """
        月次収入サマリーを取得

        Args:
            year: 年
            month: 月
            include_previous_change: 前月比を計算するか（無限再帰回避用）

        Returns:
            IncomeSummary

        """
        start_date = date(year, month, 1)
        # 月末日を取得
        if month == 12:
            end_date = date(year, 12, 31)
        else:
            next_month_start = date(year, month + 1, 1)
            end_timestamp = pd.Timestamp(next_month_start) - pd.Timedelta(days=1)
            end_date = end_timestamp.date()

        # 収入レコードを抽出
        income_records = self.extract_income_records(start_date, end_date)

        if income_records.empty:
            return IncomeSummary(
                year=year,
                month=month,
                total_income=Decimal("0"),
                category_breakdown={
                    cat: Decimal("0") for cat in IncomeCategory.all_categories()
                },
                category_ratios={
                    cat: Decimal("0") for cat in IncomeCategory.all_categories()
                },
                previous_period_change=None,
                average_monthly=None,
            )

        # カテゴリ分類
        income_records["income_category"] = income_records.apply(
            self.classify_income, axis=1
        )

        # カテゴリ別集計
        category_breakdown = {}
        for cat in IncomeCategory.all_categories():
            cat_sum = income_records[income_records["income_category"] == cat][
                "金額（円）"
            ].sum()
            category_breakdown[cat] = Decimal(str(cat_sum))

        # 総収入
        total_income = sum(category_breakdown.values())

        # 構成比率
        category_ratios = {}
        for cat, amount in category_breakdown.items():
            if total_income > 0:
                ratio = (amount / total_income) * 100
                category_ratios[cat] = ratio.quantize(Decimal("0.01"))
            else:
                category_ratios[cat] = Decimal("0")

        # 前月比を計算（無限再帰を防ぐため条件付き）
        if include_previous_change:
            previous_period_change = self._calculate_previous_month_change(year, month)
        else:
            previous_period_change = None

        return IncomeSummary(
            year=year,
            month=month,
            total_income=total_income,
            category_breakdown=category_breakdown,
            category_ratios=category_ratios,
            previous_period_change=previous_period_change,
            average_monthly=None,
        )

    def get_annual_summary(self, year: int) -> IncomeSummary:
        """
        年次収入サマリーを取得

        Args:
            year: 年

        Returns:
            IncomeSummary

        """
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        # 収入レコードを抽出
        income_records = self.extract_income_records(start_date, end_date)

        if income_records.empty:
            return IncomeSummary(
                year=year,
                month=None,
                total_income=Decimal("0"),
                category_breakdown={
                    cat: Decimal("0") for cat in IncomeCategory.all_categories()
                },
                category_ratios={
                    cat: Decimal("0") for cat in IncomeCategory.all_categories()
                },
                previous_period_change=None,
                average_monthly=Decimal("0"),
            )

        # カテゴリ分類
        income_records["income_category"] = income_records.apply(
            self.classify_income, axis=1
        )

        # カテゴリ別集計
        category_breakdown = {}
        for cat in IncomeCategory.all_categories():
            cat_sum = income_records[income_records["income_category"] == cat][
                "金額（円）"
            ].sum()
            category_breakdown[cat] = Decimal(str(cat_sum))

        # 総収入
        total_income = sum(category_breakdown.values())

        # 構成比率
        category_ratios = {}
        for cat, amount in category_breakdown.items():
            if total_income > 0:
                ratio = (amount / total_income) * 100
                category_ratios[cat] = ratio.quantize(Decimal("0.01"))
            else:
                category_ratios[cat] = Decimal("0")

        # 前年比を計算
        previous_period_change = self._calculate_previous_year_change(year)

        # 月平均
        months_with_data = income_records["日付"].dt.to_period("M").nunique()
        average_monthly = (
            (total_income / months_with_data).quantize(Decimal("0.01"))
            if months_with_data > 0
            else Decimal("0")
        )

        return IncomeSummary(
            year=year,
            month=None,
            total_income=total_income,
            category_breakdown=category_breakdown,
            category_ratios=category_ratios,
            previous_period_change=previous_period_change,
            average_monthly=average_monthly,
        )

    def _calculate_previous_month_change(self, year: int, month: int) -> Decimal | None:
        """
        前月比を計算

        Args:
            year: 年
            month: 月

        Returns:
            前月比（%）、データがない場合はNone

        """
        # 前月を取得
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1

        try:
            current_summary = self.get_monthly_summary(
                year, month, include_previous_change=False
            )
            prev_summary = self.get_monthly_summary(
                prev_year, prev_month, include_previous_change=False
            )

            if prev_summary.total_income == 0:
                return None

            change = (
                (current_summary.total_income - prev_summary.total_income)
                / prev_summary.total_income
                * 100
            )
            return change.quantize(Decimal("0.01"))
        except Exception:
            return None

    def _calculate_previous_year_change(self, year: int) -> Decimal | None:
        """
        前年比を計算

        Args:
            year: 年

        Returns:
            前年比（%）、データがない場合はNone

        """
        try:
            current_summary = self.get_annual_summary(year)
            prev_summary = self.get_annual_summary(year - 1)

            if prev_summary.total_income == 0:
                return None

            change = (
                (current_summary.total_income - prev_summary.total_income)
                / prev_summary.total_income
                * 100
            )
            return change.quantize(Decimal("0.01"))
        except Exception:
            return None

    def _load_category_rules(self) -> dict:
        """
        カテゴリ分類ルールを income_categories.json から読み込み

        Returns:
            カテゴリルール辞書

        """
        # デフォルトルール
        default_rules = {
            "salary": {
                "category": IncomeCategory.SALARY,
                "large_keywords": ["給与"],
                "medium_keywords": ["給与", "賞与", "ボーナス"],
            },
            "business": {
                "category": IncomeCategory.BUSINESS,
                "large_keywords": ["事業収入"],
                "medium_keywords": ["事業"],
            },
            "real_estate": {
                "category": IncomeCategory.REAL_ESTATE,
                "large_keywords": ["不動産"],
                "medium_keywords": ["家賃収入", "不動産収入"],
            },
            "dividend": {
                "category": IncomeCategory.DIVIDEND,
                "large_keywords": ["金融収入"],
                "medium_keywords": ["配当", "利子", "分配金"],
            },
        }

        # カスタムルールファイルを探す
        config_path = Path(__file__).parent.parent / "config" / "income_categories.json"

        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    custom_rules = json.load(f)
                    # カスタムルールでデフォルトを上書き
                    default_rules.update(custom_rules)
            except Exception:
                # ファイル読み込みエラーはデフォルトルールを使用
                pass

        return default_rules
