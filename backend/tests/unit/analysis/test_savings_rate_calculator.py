"""SavingsRateCalculator 最適化版単体テスト

TASK-2004: Phase 1 単体テスト
"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from household_mcp.analysis.income_analyzer import IncomeAnalyzer, IncomeSummary
from household_mcp.analysis.savings_rate_calculator import (
    SavingsMetrics,
    SavingsRateCalculator,
)
from household_mcp.dataloader import HouseholdDataLoader


@pytest.fixture
def mock_data_loader():
    """モックデータローダー"""
    return Mock(spec=HouseholdDataLoader)


@pytest.fixture
def mock_income_analyzer():
    """モックIncomeAnalyzer"""
    return Mock(spec=IncomeAnalyzer)


@pytest.fixture
def calculator(mock_income_analyzer, mock_data_loader):
    """SavingsRateCalculator インスタンス"""
    return SavingsRateCalculator(mock_income_analyzer, mock_data_loader)


class TestCostTypeClassification:
    """固定費・変動費分類テスト"""

    def test_classify_fixed_cost_housing(self, calculator):
        """住宅費は固定費"""
        record = pd.Series({"大項目": "住宅", "中項目": "家賃"})
        result = calculator.classify_cost_type(record)
        assert result == "fixed"

    def test_classify_fixed_cost_utilities(self, calculator):
        """水道光熱費は固定費"""
        record = pd.Series({"大項目": "水道光熱費", "中項目": "電気"})
        result = calculator.classify_cost_type(record)
        assert result == "fixed"

    def test_classify_variable_cost(self, calculator):
        """その他は変動費"""
        record = pd.Series({"大項目": "食費", "中項目": "食料品"})
        result = calculator.classify_cost_type(record)
        assert result == "variable"


class TestMonthlySavingsRate:
    """月次貯蓄率計算テスト"""

    def test_calculate_basic_savings_rate(
        self, calculator, mock_income_analyzer, mock_data_loader
    ):
        """基本的な貯蓄率計算"""
        # 収入300000円
        income_summary = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("300000"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        mock_income_analyzer.get_monthly_summary.return_value = income_summary

        # 支出データ（固定費・変動費混在）
        expense_data = pd.DataFrame(
            {
                "日付": pd.to_datetime(["2024-07-01", "2024-07-05"]),
                "金額（円）": [-100000, -50000],
                "計算対象": [1, 1],
                "大項目": ["住宅", "食費"],
                "中項目": ["家賃", "食料品"],
            }
        )
        mock_data_loader.load.return_value = expense_data

        metrics = calculator.calculate_monthly_savings_rate(2024, 7)

        assert metrics.year == 2024
        assert metrics.month == 7
        assert metrics.income == Decimal("300000.00")
        # 支出合計: 150000
        assert metrics.expense == Decimal("150000.00")
        # 貯蓄: 300000-150000 = 150000
        assert metrics.savings == Decimal("150000.00")
        # 貯蓄率: (150000 / 300000) * 100 = 50.00%
        assert metrics.savings_rate == Decimal("50.00")

    def test_negative_savings_deficit(
        self, calculator, mock_income_analyzer, mock_data_loader
    ):
        """赤字（負の貯蓄）の場合"""
        income_summary = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("100000"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        mock_income_analyzer.get_monthly_summary.return_value = income_summary

        expense_data = pd.DataFrame(
            {
                "日付": pd.to_datetime(["2024-07-01"]),
                "金額（円）": [-200000],
                "計算対象": [1],
                "大項目": ["食費"],
                "中項目": ["外食"],
            }
        )
        mock_data_loader.load.return_value = expense_data

        metrics = calculator.calculate_monthly_savings_rate(2024, 7)

        # 貯蓄: 100000 - 200000 = -100000
        assert metrics.savings == Decimal("-100000.00")
        # 貯蓄率: (-100000 / 100000) * 100 = -100.00%
        assert metrics.savings_rate == Decimal("-100.00")


class TestSavingsMetricsDataclass:
    """SavingsMetricsデータクラステスト"""

    def test_to_dict_conversion(self):
        """辞書変換が正しく動作する"""
        metrics = SavingsMetrics(
            year=2024,
            month=7,
            income=Decimal("300000.00"),
            expense=Decimal("200000.00"),
            savings=Decimal("100000.00"),
            savings_rate=Decimal("33.33"),
            disposable_income=Decimal("250000.00"),
            fixed_costs=Decimal("50000.00"),
            variable_costs=Decimal("150000.00"),
            variable_cost_ratio=Decimal("60.00"),
        )

        result = metrics.to_dict()

        assert result["year"] == 2024
        assert result["income"] == 300000.0
        assert isinstance(result["savings_rate"], float)
