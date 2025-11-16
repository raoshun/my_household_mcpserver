"""IncomeAnalyzer 単体テスト

TASK-2004: Phase 1 単体テスト
"""
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

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
    loader = Mock(spec=HouseholdDataLoader)
    return loader


@pytest.fixture
def sample_income_data():
    """サンプル収入データ"""
    return pd.DataFrame(
        {
            "日付": pd.to_datetime(
                [
                    "2024-07-01",
                    "2024-07-05",
                    "2024-07-10",
                    "2024-07-15",
                    "2024-07-20",
                ]
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
        assert IncomeCategory.SALARY in categories
        assert IncomeCategory.BUSINESS in categories
        assert IncomeCategory.REAL_ESTATE in categories
        assert IncomeCategory.DIVIDEND in categories
        assert IncomeCategory.OTHER in categories


class TestIncomeAnalyzerExtraction:
    """収入抽出テスト"""

    def test_extract_income_records_positive_only(
        self, income_analyzer, mock_data_loader, sample_income_data
    ):
        """金額が正のレコードのみ抽出される"""
        mock_data_loader.load.return_value = sample_income_data

        result = income_analyzer.extract_income_records(
            date(2024, 7, 1), date(2024, 7, 31)
        )

        # 正の金額: 300000, 50000, 10000
        assert len(result) == 3
        assert all(result["金額（円）"] > 0)

    def test_extract_income_records_with_calculation_flag(
        self, income_analyzer, mock_data_loader
    ):
        """計算対象=1のみ抽出される"""
        data = pd.DataFrame(
            {
                "日付": pd.to_datetime(["2024-07-01", "2024-07-02", "2024-07-03"]),
                "金額（円）": [100000, 200000, 300000],
                "計算対象": [1, 0, 1],
                "大項目": ["給与", "給与", "給与"],
                "中項目": ["給与", "給与", "給与"],
            }
        )
        mock_data_loader.load.return_value = data

        result = income_analyzer.extract_income_records(
            date(2024, 7, 1), date(2024, 7, 31)
        )

        assert len(result) == 2
        assert all(result["計算対象"] == 1)

    def test_extract_income_records_date_range_filter(
        self, income_analyzer, mock_data_loader
    ):
        """日付範囲でフィルタされる"""
        data = pd.DataFrame(
            {
                "日付": pd.to_datetime(
                    ["2024-06-30", "2024-07-01", "2024-07-31", "2024-08-01"]
                ),
                "金額（円）": [100000, 200000, 300000, 400000],
                "計算対象": [1, 1, 1, 1],
                "大項目": ["給与", "給与", "給与", "給与"],
                "中項目": ["給与", "給与", "給与", "給与"],
            }
        )
        mock_data_loader.load.return_value = data

        result = income_analyzer.extract_income_records(
            date(2024, 7, 1), date(2024, 7, 31)
        )

        assert len(result) == 2
        assert result["金額（円）"].tolist() == [200000, 300000]

    def test_extract_income_records_empty_when_no_data(
        self, income_analyzer, mock_data_loader
    ):
        """データがない場合は空DataFrame"""
        mock_data_loader.load.side_effect = FileNotFoundError()

        result = income_analyzer.extract_income_records(
            date(2024, 7, 1), date(2024, 7, 31)
        )

        assert result.empty


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

    def test_classify_income_by_medium_category(self, income_analyzer):
        """中項目でも分類できる"""
        record = pd.Series({"大項目": "収入", "中項目": "賞与"})
        result = income_analyzer.classify_income(record)
        assert result == IncomeCategory.SALARY


class TestMonthlySummary:
    """月次サマリーテスト"""

    def test_get_monthly_summary_basic(
        self, income_analyzer, mock_data_loader, sample_income_data
    ):
        """基本的な月次サマリー取得"""
        mock_data_loader.load.return_value = sample_income_data

        summary = income_analyzer.get_monthly_summary(2024, 7)

        assert summary.year == 2024
        assert summary.month == 7
        assert summary.total_income > 0
        assert len(summary.category_breakdown) == 5
        assert len(summary.category_ratios) == 5

    def test_get_monthly_summary_total_income_correct(
        self, income_analyzer, mock_data_loader, sample_income_data
    ):
        """総収入が正しく計算される"""
        mock_data_loader.load.return_value = sample_income_data

        summary = income_analyzer.get_monthly_summary(2024, 7)

        # 正の金額: 300000 + 50000 + 10000 = 360000
        assert summary.total_income == Decimal("360000")

    def test_get_monthly_summary_category_breakdown(
        self, income_analyzer, mock_data_loader, sample_income_data
    ):
        """カテゴリ別内訳が正しい"""
        mock_data_loader.load.return_value = sample_income_data

        summary = income_analyzer.get_monthly_summary(2024, 7)

        assert summary.category_breakdown[IncomeCategory.SALARY] == Decimal("300000")
        assert summary.category_breakdown[IncomeCategory.DIVIDEND] == Decimal("10000")
        assert summary.category_breakdown[IncomeCategory.OTHER] == Decimal("50000")

    def test_get_monthly_summary_ratios_sum_to_100(
        self, income_analyzer, mock_data_loader, sample_income_data
    ):
        """構成比率の合計が100%"""
        mock_data_loader.load.return_value = sample_income_data

        summary = income_analyzer.get_monthly_summary(2024, 7)

        total_ratio = sum(summary.category_ratios.values())
        assert abs(total_ratio - Decimal("100")) < Decimal("0.01")

    def test_get_monthly_summary_empty_data(self, income_analyzer, mock_data_loader):
        """データがない場合は0を返す"""
        mock_data_loader.load.side_effect = FileNotFoundError()

        summary = income_analyzer.get_monthly_summary(2024, 7)

        assert summary.total_income == Decimal("0")
        assert all(v == Decimal("0") for v in summary.category_breakdown.values())


class TestAnnualSummary:
    """年次サマリーテスト"""

    def test_get_annual_summary_basic(self, income_analyzer, mock_data_loader):
        """基本的な年次サマリー取得"""
        # 複数月のデータをモック
        def load_side_effect(year, month):
            return pd.DataFrame(
                {
                    "日付": pd.to_datetime([f"{year}-{month:02d}-01"]),
                    "金額（円）": [100000 * month],
                    "計算対象": [1],
                    "大項目": ["給与"],
                    "中項目": ["給与"],
                }
            )

        mock_data_loader.load.side_effect = load_side_effect

        summary = income_analyzer.get_annual_summary(2024)

        assert summary.year == 2024
        assert summary.month is None
        assert summary.total_income > 0
        assert summary.average_monthly is not None

    def test_get_annual_summary_average_monthly(
        self, income_analyzer, mock_data_loader
    ):
        """月平均が正しく計算される"""

        def load_side_effect(year, month):
            return pd.DataFrame(
                {
                    "日付": pd.to_datetime([f"{year}-{month:02d}-15"]),
                    "金額（円）": [100000],
                    "計算対象": [1],
                    "大項目": ["給与"],
                    "中項目": ["給与"],
                }
            )

        mock_data_loader.load.side_effect = load_side_effect

        summary = income_analyzer.get_annual_summary(2024)

        # 12ヶ月分: 100000 * 12 = 1200000, 平均: 100000
        assert summary.total_income == Decimal("1200000")
        assert summary.average_monthly == Decimal("100000.00")


class TestIncomeSummaryDataclass:
    """IncomeSummaryデータクラステスト"""

    def test_to_dict_conversion(self):
        """辞書変換が正しく動作する"""
        summary = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("100000"),
            category_breakdown={IncomeCategory.SALARY: Decimal("100000")},
            category_ratios={IncomeCategory.SALARY: Decimal("100.00")},
            previous_period_change=Decimal("10.50"),
            average_monthly=None,
        )

        result = summary.to_dict()

        assert result["year"] == 2024
        assert result["month"] == 7
        assert result["total_income"] == 100000.0
        assert result["previous_period_change"] == 10.50
        assert result["average_monthly"] is None
