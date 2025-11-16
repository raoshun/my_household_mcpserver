"""SavingsRateCalculator 単体テスト

TASK-2004: Phase 1 単体テスト
"""
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

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
    loader = Mock(spec=HouseholdDataLoader)
    return loader


@pytest.fixture
def mock_income_analyzer():
    """モックIncomeAnalyzer"""
    analyzer = Mock(spec=IncomeAnalyzer)
    return analyzer


@pytest.fixture
def sample_expense_data():
    """サンプル支出データ（固定費・変動費混在）"""
    return pd.DataFrame(
        {
            "日付": pd.to_datetime(
                ["2024-07-01", "2024-07-05", "2024-07-10", "2024-07-15", "2024-07-20"]
            ),
            "金額（円）": [-100000, -50000, -30000, -20000, -10000],
            "計算対象": [1, 1, 1, 1, 1],
            "大項目": ["住宅", "食費", "水道光熱費", "交通費", "娯楽"],
            "中項目": ["家賃", "食料品", "電気", "電車", "映画"],
        }
    )


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

    def test_classify_fixed_cost_communication(self, calculator):
        """通信費は固定費"""
        record = pd.Series({"大項目": "通信費", "中項目": "携帯電話"})
        result = calculator.classify_cost_type(record)
        assert result == "fixed"

    def test_classify_fixed_cost_insurance(self, calculator):
        """保険は固定費"""
        record = pd.Series({"大項目": "保険", "中項目": "生命保険"})
        result = calculator.classify_cost_type(record)
        assert result == "fixed"

    def test_classify_variable_cost(self, calculator):
        """その他は変動費"""
        record = pd.Series({"大項目": "食費", "中項目": "食料品"})
        result = calculator.classify_cost_type(record)
        assert result == "variable"

    def test_classify_cost_by_medium_category(self, calculator):
        """中項目でも固定費判定できる"""
        record = pd.Series({"大項目": "生活費", "中項目": "水道代"})
        result = calculator.classify_cost_type(record)
        assert result == "fixed"


class TestMonthlySavingsRate:
    """月次貯蓄率計算テスト"""

    def test_calculate_basic_savings_rate(
        self,
        calculator,
        mock_income_analyzer,
        mock_data_loader,
        sample_expense_data,
    ):
        """基本的な貯蓄率計算"""
        # 収入300000円
        mock_income_analyzer.get_monthly_summary.return_value = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("300000"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        mock_data_loader.load.return_value = sample_expense_data

        metrics = calculator.calculate_monthly_savings_rate(2024, 7)

        assert metrics.year == 2024
        assert metrics.month == 7
        assert metrics.income == Decimal("300000.00")
        # 支出合計: 100000+50000+30000+20000+10000 = 210000
        assert metrics.expense == Decimal("210000.00")
        # 貯蓄: 300000-210000 = 90000
        assert metrics.savings == Decimal("90000.00")

    def test_savings_rate_percentage_calculation(
        self,
        calculator,
        mock_income_analyzer,
        mock_data_loader,
        sample_expense_data,
    ):
        """貯蓄率パーセンテージが正しい"""
        mock_income_analyzer.get_monthly_summary.return_value = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("300000"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        mock_data_loader.load.return_value = sample_expense_data

        metrics = calculator.calculate_monthly_savings_rate(2024, 7)

        # 貯蓄率: (90000 / 300000) * 100 = 30.00%
        assert metrics.savings_rate == Decimal("30.00")

    def test_fixed_and_variable_costs_separation(
        self,
        calculator,
        mock_income_analyzer,
        mock_data_loader,
        sample_expense_data,
    ):
        """固定費と変動費が正しく分離される"""
        mock_income_analyzer.get_monthly_summary.return_value = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("300000"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        mock_data_loader.load.return_value = sample_expense_data

        metrics = calculator.calculate_monthly_savings_rate(2024, 7)

        # 固定費: 住宅100000 + 水道30000 = 130000
        assert metrics.fixed_costs == Decimal("130000.00")
        # 変動費: 食費50000 + 交通20000 + 娯楽10000 = 80000
        assert metrics.variable_costs == Decimal("80000.00")

    def test_disposable_income_calculation(
        self,
        calculator,
        mock_income_analyzer,
        mock_data_loader,
        sample_expense_data,
    ):
        """可処分所得が正しく計算される"""
        mock_income_analyzer.get_monthly_summary.return_value = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("300000"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        mock_data_loader.load.return_value = sample_expense_data

        metrics = calculator.calculate_monthly_savings_rate(2024, 7)

        # 可処分所得: 300000 - 130000(固定費) = 170000
        assert metrics.disposable_income == Decimal("170000.00")

    def test_variable_cost_ratio_calculation(
        self,
        calculator,
        mock_income_analyzer,
        mock_data_loader,
        sample_expense_data,
    ):
        """変動費率が正しく計算される"""
        mock_income_analyzer.get_monthly_summary.return_value = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("300000"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        mock_data_loader.load.return_value = sample_expense_data

        metrics = calculator.calculate_monthly_savings_rate(2024, 7)

        # 変動費率: (80000 / 170000) * 100 ≈ 47.06%
        assert abs(metrics.variable_cost_ratio - Decimal("47.06")) < Decimal("0.01")

    def test_negative_savings_deficit(
        self, calculator, mock_income_analyzer, mock_data_loader
    ):
        """赤字（負の貯蓄）の場合も正しく計算"""
        mock_income_analyzer.get_monthly_summary.return_value = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("100000"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        # 支出200000円
        mock_data_loader.load.return_value = pd.DataFrame(
            {
                "日付": pd.to_datetime(["2024-07-01"]),
                "金額（円）": [-200000],
                "計算対象": [1],
                "大項目": ["食費"],
                "中項目": ["外食"],
            }
        )

        metrics = calculator.calculate_monthly_savings_rate(2024, 7)

        # 貯蓄: 100000 - 200000 = -100000
        assert metrics.savings == Decimal("-100000.00")
        # 貯蓄率: (-100000 / 100000) * 100 = -100.00%
        assert metrics.savings_rate == Decimal("-100.00")

    def test_zero_income_case(self, calculator, mock_income_analyzer, mock_data_loader):
        """収入ゼロの場合"""
        mock_income_analyzer.get_monthly_summary.return_value = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("0"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        mock_data_loader.load.return_value = pd.DataFrame()

        metrics = calculator.calculate_monthly_savings_rate(2024, 7)

        assert metrics.income == Decimal("0.00")
        assert metrics.savings_rate == Decimal("0")

    def test_no_expense_data(
        self, calculator, mock_income_analyzer, mock_data_loader
    ):
        """支出データがない場合は収入全額が貯蓄"""
        mock_income_analyzer.get_monthly_summary.return_value = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("300000"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        mock_data_loader.load.return_value = pd.DataFrame()

        metrics = calculator.calculate_monthly_savings_rate(2024, 7)

        assert metrics.savings == Decimal("300000.00")
        assert metrics.savings_rate == Decimal("100.00")


class TestSavingsRateTrend:
    """貯蓄率推移テスト"""

    def test_get_savings_rate_trend_multiple_months(
        self, calculator, mock_income_analyzer, mock_data_loader
    ):
        """複数月の推移取得"""
        mock_income_analyzer.get_monthly_summary.return_value = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("300000"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        mock_data_loader.load.return_value = pd.DataFrame(
            {
                "日付": pd.to_datetime(["2024-07-01"]),
                "金額（円）": [-100000],
                "計算対象": [1],
                "大項目": ["食費"],
                "中項目": ["食料品"],
            }
        )

        trend = calculator.get_savings_rate_trend(date(2024, 7, 1), date(2024, 9, 30))

        assert len(trend) == 3  # 7月、8月、9月
        assert all(isinstance(m, SavingsMetrics) for m in trend)

    def test_get_savings_rate_trend_single_month(
        self, calculator, mock_income_analyzer, mock_data_loader
    ):
        """単月でも動作する"""
        mock_income_analyzer.get_monthly_summary.return_value = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("300000"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        mock_data_loader.load.return_value = pd.DataFrame()

        trend = calculator.get_savings_rate_trend(date(2024, 7, 1), date(2024, 7, 31))

        assert len(trend) == 1


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
        assert result["month"] == 7
        assert result["income"] == 300000.0
        assert result["savings_rate"] == 33.33
        assert isinstance(result["savings_rate"], float)


class TestPrecisionRequirement:
    """NFR-038: 数値精度テスト（小数第2位）"""

    def test_savings_rate_precision(
        self, calculator, mock_income_analyzer, mock_data_loader
    ):
        """貯蓄率が小数第2位まで"""
        mock_income_analyzer.get_monthly_summary.return_value = IncomeSummary(
            year=2024,
            month=7,
            total_income=Decimal("300000"),
            category_breakdown={},
            category_ratios={},
            previous_period_change=None,
            average_monthly=None,
        )
        mock_data_loader.load.return_value = pd.DataFrame(
            {
                "日付": pd.to_datetime(["2024-07-01"]),
                "金額（円）": [-100001],
                "計算対象": [1],
                "大項目": ["食費"],
                "中項目": ["食料品"],
            }
        )

        metrics = calculator.calculate_monthly_savings_rate(2024, 7)

        # 貯蓄率の小数点以下桁数確認
        str_rate = str(metrics.savings_rate)
        if "." in str_rate:
            decimal_places = len(str_rate.split(".")[1])
            assert decimal_places <= 2
