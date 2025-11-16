"""
収入分析モジュール

家計簿CSVデータから収入を抽出・分類し、月次/年次サマリーを生成する。
"""

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import pandas as pd

from household_mcp.database.manager import DatabaseManager
from household_mcp.database.models import IncomeSnapshot
from household_mcp.dataloader import HouseholdDataLoader

# NFR-040: キャッシュ有効期間（秒） - 1時間
CACHE_TTL_SECONDS = 3600


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

    def __init__(
        self,
        data_loader: HouseholdDataLoader,
        db_manager: DatabaseManager | None = None,
    ):
        """
        Initialize IncomeAnalyzer.

        Args:
            data_loader: 家計簿データローダー
            db_manager: データベースマネージャー（キャッシング用、省略時は無効）

        """
        self.data_loader = data_loader
        self.db_manager = db_manager
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
        月次収入サマリーを取得（キャッシュ対応 - TASK-2015）

        Args:
            year: 年
            month: 月
            include_previous_change: 前月比を計算するか（無限再帰回避用）

        Returns:
            IncomeSummary

        """
        # キャッシュチェック（NFR-040: 1時間有効）
        cached_snapshot = self._get_cached_snapshot(year, month)
        if cached_snapshot is not None:
            return self._load_summary_from_snapshot(cached_snapshot)

        # キャッシュミス - CSVから計算
        start_date = date(year, month, 1)
        # 月末日を取得
        if month == 12:
            end_date = date(year, 12, 31)
        else:
            next_month_start = date(year, month + 1, 1)
            next_month_ts = pd.Timestamp(next_month_start)
            end_timestamp = next_month_ts - pd.Timedelta(days=1)
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
            prev_change = self._calculate_previous_month_change(year, month)
        else:
            prev_change = None

        summary = IncomeSummary(
            year=year,
            month=month,
            total_income=total_income,
            category_breakdown=category_breakdown,
            category_ratios=category_ratios,
            previous_period_change=prev_change,
            average_monthly=None,
        )

        # キャッシュに保存
        self._save_snapshot_to_cache(summary)

        return summary

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

        # 月平均（年次は12ヶ月で平均化）
        average_monthly = (
            (total_income / Decimal("12")).quantize(Decimal("0.01"))
            if total_income > 0
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
            current_total = self._compute_annual_total(year)
            prev_total = self._compute_annual_total(year - 1)

            if prev_total == 0:
                return None

            change = ((current_total - prev_total) / prev_total) * 100
            return change.quantize(Decimal("0.01"))
        except Exception:
            return None

    def _compute_annual_total(self, year: int) -> Decimal:
        """
        年指定の総収入合計のみを計算（副作用なし、再帰回避用）

        Args:
            year: 年

        Returns:
            総収入（Decimal）。データがない場合は Decimal("0")。

        """
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        income_records = self.extract_income_records(start_date, end_date)
        if income_records.empty:
            return Decimal("0")

        income_records["income_category"] = income_records.apply(
            self.classify_income, axis=1
        )

        total = Decimal("0")
        for cat in IncomeCategory.all_categories():
            cat_sum = income_records[income_records["income_category"] == cat][
                "金額（円）"
            ].sum()
            total += Decimal(str(cat_sum))

        return total

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
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "income_categories.json"

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

    def _get_cached_snapshot(self, year: int, month: int) -> IncomeSnapshot | None:
        """
        キャッシュから収入スナップショットを取得（TASK-2015）

        Args:
            year: 年
            month: 月

        Returns:
            キャッシュされたスナップショット（存在しない or 期限切れの場合はNone）

        """
        if self.db_manager is None:
            return None

        snapshot_month = f"{year:04d}-{month:02d}"

        with self.db_manager.get_session() as session:
            snapshot = (
                session.query(IncomeSnapshot)
                .filter(IncomeSnapshot.snapshot_month == snapshot_month)
                .first()
            )

            if snapshot is None:
                return None

            # NFR-040: キャッシュ有効期間チェック（1時間）
            now = datetime.now()
            cache_age = (now - snapshot.updated_at).total_seconds()

            if cache_age > CACHE_TTL_SECONDS:
                # 期限切れ
                return None

            return snapshot

    def _save_snapshot_to_cache(self, summary: IncomeSummary) -> None:
        """
        収入サマリーをキャッシュに保存（TASK-2015）

        Args:
            summary: 収入サマリー

        """
        if self.db_manager is None or summary.month is None:
            return

        snapshot_month = f"{summary.year:04d}-{summary.month:02d}"

        # カテゴリ別金額を整数に変換（単位:円）
        salary = int(
            summary.category_breakdown.get(IncomeCategory.SALARY, Decimal("0"))
        )
        business = int(
            summary.category_breakdown.get(IncomeCategory.BUSINESS, Decimal("0"))
        )
        real_estate = int(
            summary.category_breakdown.get(IncomeCategory.REAL_ESTATE, Decimal("0"))
        )
        dividend = int(
            summary.category_breakdown.get(IncomeCategory.DIVIDEND, Decimal("0"))
        )
        other = int(summary.category_breakdown.get(IncomeCategory.OTHER, Decimal("0")))
        total = int(summary.total_income)

        with self.db_manager.get_session() as session:
            # Upsert: 既存レコードがあれば更新、なければ挿入
            snapshot = (
                session.query(IncomeSnapshot)
                .filter(IncomeSnapshot.snapshot_month == snapshot_month)
                .first()
            )

            if snapshot:
                # 更新
                snapshot.salary_income = salary  # type: ignore[assignment]
                snapshot.business_income = business  # type: ignore[assignment]
                snapshot.real_estate_income = real_estate  # type: ignore[assignment]
                snapshot.dividend_income = dividend  # type: ignore[assignment]
                snapshot.other_income = other  # type: ignore[assignment]
                snapshot.total_income = total  # type: ignore[assignment]
                snapshot.savings_rate = None  # type: ignore[assignment] 将来の拡張用
                snapshot.updated_at = datetime.now()  # type: ignore[assignment]
            else:
                # 新規挿入
                snapshot = IncomeSnapshot(
                    snapshot_month=snapshot_month,
                    salary_income=salary,
                    business_income=business,
                    real_estate_income=real_estate,
                    dividend_income=dividend,
                    other_income=other,
                    total_income=total,
                    savings_rate=None,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                session.add(snapshot)

            session.commit()

    def _load_summary_from_snapshot(self, snapshot: IncomeSnapshot) -> IncomeSummary:
        """
        スナップショットからIncomeSummaryを復元

        Args:
            snapshot: キャッシュされたスナップショット

        Returns:
            収入サマリー

        """
        year, month = map(int, snapshot.snapshot_month.split("-"))

        salary_val = cast(int, snapshot.salary_income)
        business_val = cast(int, snapshot.business_income)
        real_estate_val = cast(int, snapshot.real_estate_income)
        dividend_val = cast(int, snapshot.dividend_income)
        other_val = cast(int, snapshot.other_income)
        total_val = cast(int, snapshot.total_income)

        category_breakdown = {
            IncomeCategory.SALARY: Decimal(salary_val),
            IncomeCategory.BUSINESS: Decimal(business_val),
            IncomeCategory.REAL_ESTATE: Decimal(real_estate_val),
            IncomeCategory.DIVIDEND: Decimal(dividend_val),
            IncomeCategory.OTHER: Decimal(other_val),
        }

        total = Decimal(total_val)

        # 構成比率を計算
        category_ratios = {}
        for cat, amount in category_breakdown.items():
            if total > 0:
                ratio = (amount / total * Decimal("100")).quantize(Decimal("0.01"))
                category_ratios[cat] = ratio
            else:
                category_ratios[cat] = Decimal("0")

        return IncomeSummary(
            year=year,
            month=month,
            total_income=total,
            category_breakdown=category_breakdown,
            category_ratios=category_ratios,
            previous_period_change=None,  # キャッシュには保存しない
            average_monthly=None,
        )
