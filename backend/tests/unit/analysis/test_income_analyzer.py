"""IncomeAnalyzer 最適化版単体テスト

TASK-2004: Phase 1 単体テスト (最適化版)
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from household_mcp.analysis.income_analyzer import (
    IncomeAnalyzer,
    IncomeCategory,
    IncomeSummary,
)
from household_mcp.dataloader import HouseholdDataLoader


@pytest.fixture
def mock_data_loader():
    """モックデータローダー"""
    return Mock(spec=HouseholdDataLoader)


@pytest.fixture
def sample_income_data():
    """サンプル収入データ"""
    return pd.DataFrame(
        {
            "日付": pd.to_datetime(
                ["2024-07-01", "2024-07-05", "2024-07-10", "2024-07-15", "2024-07-20"]
            ),
            "金額（円）": [300000, 50000, -80000, 10000, -50000],
            "計算対象": [1, 1, 1, 1, 1],
            "大項目": ["給与", "その他", "食費", "金融収入", "交通費"],
            "中項目": ["給与", "還付金", "食料品", "配当", "電車"],
        }
    )


@pytest.fixture
def income_analyzer(mock_data_loader):
    """IncomeAnalyzer インスタンス"""
    return IncomeAnalyzer(mock_data_loader)


class TestIncomeCategory:
    """IncomeCategoryクラステスト"""

    def test_all_categories_returns_five_types(self):
        """5つのカテゴリが返される"""
        categories = IncomeCategory.all_categories()
        assert len(categories) == 5


class TestIncomeClassification:
    """収入分類テスト"""

    def test_classify_income_salary(self, income_analyzer):
        """給与所得の分類"""
        record = pd.Series({"大項目": "給与", "中項目": "給与"})
        result = income_analyzer.classify_income(record)
        assert result == IncomeCategory.SALARY

    def test_classify_income_business(self, income_analyzer):
        """事業所得の分類"""
        record = pd.Series({"大項目": "事業収入", "中項目": "売上"})
        result = income_analyzer.classify_income(record)
        assert result == IncomeCategory.BUSINESS

    def test_classify_income_real_estate(self, income_analyzer):
        """不動産所得の分類"""
        record = pd.Series({"大項目": "不動産", "中項目": "家賃収入"})
        result = income_analyzer.classify_income(record)
        assert result == IncomeCategory.REAL_ESTATE

    def test_classify_income_dividend(self, income_analyzer):
        """配当・利子所得の分類"""
        record = pd.Series({"大項目": "金融収入", "中項目": "配当"})
        result = income_analyzer.classify_income(record)
        assert result == IncomeCategory.DIVIDEND

    def test_classify_income_other(self, income_analyzer):
        """その他収入の分類"""
        record = pd.Series({"大項目": "その他", "中項目": "還付金"})
        result = income_analyzer.classify_income(record)
        assert result == IncomeCategory.OTHER


class TestMonthlySummary:
    """月次サマリーテスト（extract_income_recordsをモック）"""

    def test_get_monthly_summary_basic(self, income_analyzer, sample_income_data):
        """基本的な月次サマリー取得"""
        # 収入レコードのみをモックで返す
        income_only = sample_income_data[sample_income_data["金額（円）"] > 0].copy()

        with (
            patch.object(
                income_analyzer, "extract_income_records", return_value=income_only
            ),
            patch.object(
                income_analyzer, "_calculate_previous_month_change", return_value=None
            ),
        ):
            summary = income_analyzer.get_monthly_summary(2024, 7)

        assert summary.year == 2024
        assert summary.month == 7
        # 300000 + 50000 + 10000 = 360000
        assert summary.total_income == Decimal("360000")

    def test_get_monthly_summary_category_breakdown(
        self, income_analyzer, sample_income_data
    ):
        """カテゴリ別内訳が正しい"""
        income_only = sample_income_data[sample_income_data["金額（円）"] > 0].copy()

        with (
            patch.object(
                income_analyzer, "extract_income_records", return_value=income_only
            ),
            patch.object(
                income_analyzer, "_calculate_previous_month_change", return_value=None
            ),
        ):
            summary = income_analyzer.get_monthly_summary(2024, 7)

        assert summary.category_breakdown[IncomeCategory.SALARY] == Decimal("300000")
        assert summary.category_breakdown[IncomeCategory.DIVIDEND] == Decimal("10000")
        assert summary.category_breakdown[IncomeCategory.OTHER] == Decimal("50000")

    def test_get_monthly_summary_empty_data(self, income_analyzer):
        """データがない場合"""
        with (
            patch.object(
                income_analyzer, "extract_income_records", return_value=pd.DataFrame()
            ),
            patch.object(
                income_analyzer, "_calculate_previous_month_change", return_value=None
            ),
        ):
            summary = income_analyzer.get_monthly_summary(2024, 7)

        assert summary.total_income == Decimal("0")


class TestAnnualSummary:
    """年次サマリーテスト（extract_income_recordsをモック）"""

    def test_get_annual_summary_basic(self, income_analyzer):
        """基本的な年次サマリー取得"""
        # 各月異なる日付でデータ作成
        dates = [f"2024-{m:02d}-15" for m in range(1, 13)]
        annual_data = pd.DataFrame(
            {
                "日付": pd.to_datetime(dates),
                "金額（円）": [100000] * 12,
                "計算対象": [1] * 12,
                "大項目": ["給与"] * 12,
                "中項目": ["給与"] * 12,
            }
        )

        with (
            patch.object(
                income_analyzer, "extract_income_records", return_value=annual_data
            ),
            patch.object(
                income_analyzer, "_calculate_previous_year_change", return_value=None
            ),
        ):
            summary = income_analyzer.get_annual_summary(2024)

        assert summary.year == 2024
        assert summary.total_income == Decimal("1200000")  # 100000 * 12
        assert summary.average_monthly == Decimal("100000")


class TestIncomeSummaryDataclass:
    """IncomeSummaryデータクラステスト"""

    def test_to_dict_conversion(self):
        """辞書変換が正しく動作する"""
        summary = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("300000"),
            category_breakdown={
                IncomeCategory.SALARY: Decimal("300000"),
            },
            category_ratios={
                IncomeCategory.SALARY: Decimal("100.00"),
            },
            previous_period_change=None,
            average_monthly=None,
        )

        result = summary.to_dict()

        assert result["year"] == 2024
        assert result["total_income"] == 300000.0
        assert isinstance(result["total_income"], float)
